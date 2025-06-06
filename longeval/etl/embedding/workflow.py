import luigi
import typer
from pyspark.ml import Pipeline
from pyspark.ml.functions import vector_to_array
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from typing_extensions import Annotated

from longeval.spark import spark_resource

from .ml import WrappedSentenceTransformer


class ProcessSentenceTransformer(luigi.Task):
    input_path = luigi.Parameter()
    output_path = luigi.Parameter()
    # we break the dataset into a number of samples that are processed in parallel
    sample_id = luigi.IntParameter()
    num_sample_ids = luigi.IntParameter(default=20)
    primary_key = luigi.Parameter(default="docid")
    feature_columns = luigi.ListParameter(default=["embedding"])
    # controls the number of partitions written to disk, must be at least the number
    # of tasks that we have in parallel to best take advantage of disk
    num_partitions = luigi.IntParameter(default=8)
    model_name = luigi.Parameter(default="all-MiniLM-L6-v2")
    batch_size = luigi.IntParameter(default=32)
    cpu_count = luigi.IntParameter(default=8)

    def output(self):
        # write a partitioned dataset to disk
        return luigi.LocalTarget(
            f"{self.output_path}/data/sample_id={self.sample_id}/_SUCCESS"
        )

    def transform(self, model, df, features) -> DataFrame:
        transformed = model.transform(df)
        for c in features:
            # check if the feature is a vector and convert it to an array
            if "array" in transformed.schema[c].simpleString():
                continue
            transformed = transformed.withColumn(c, vector_to_array(F.col(c)))
        return transformed

    def _deduplicate(self, df):
        """Deduplicate the documents based on docid and date.

        This seems like it might be pretty slow, but thankfully we only have to do this once.
        """
        window = Window.partitionBy("docid").orderBy(F.desc(F.length("contents")))
        return (
            df.where(F.length("contents") > 50)
            .withColumn("rank", F.row_number().over(window))
            .where(F.col("rank") == 1)
            .drop("rank")
        )

    def run(self):
        kwargs = {
            "cores": self.cpu_count,
            "spark.sql.shuffle.partitions": max(self.num_partitions, 200),
        }
        with spark_resource(**kwargs) as spark:
            # read the data and keep the sample we're currently processing
            df = (
                spark.read.parquet(self.input_path)
                .withColumn(
                    "sample_id", F.crc32(self.primary_key) % self.num_sample_ids
                )
                .where(F.col("sample_id") == self.sample_id)
                .drop("sample_id")
            )
            pipeline = Pipeline(
                stages=[
                    WrappedSentenceTransformer(
                        input_col="contents",
                        output_col="embedding",
                        model_name=self.model_name,
                        batch_size=self.batch_size,
                    )
                ]
            ).fit(spark.createDataFrame([[""]], ["text"]))
            df = self.transform(
                pipeline,
                self._deduplicate(df),
                self.feature_columns,
            )
            df.printSchema()
            df.explain()
            (
                df.repartition(self.num_partitions)
                .write.mode("overwrite")
                .parquet(f"{self.output_path}/sample_id={self.sample_id}")
            )


def main(
    input_path: Annotated[str, typer.Argument(help="Input root directory")],
    output_path: Annotated[str, typer.Argument(help="Output root directory")],
    sample_id: Annotated[int, typer.Option(help="Sample ID")] = None,
    num_sample_ids: Annotated[int, typer.Option(help="Number of sample IDs")] = 50,
    model_name: Annotated[str, typer.Option(help="Model name")] = "all-MiniLM-L6-v2",
    scheduler_host: Annotated[str, typer.Option(help="Scheduler host")] = None,
    cpu_count: Annotated[int, typer.Option(help="Number of CPUs")] = 8,
    batch_size: Annotated[int, typer.Option(help="Batch size")] = 32,
):
    """Count the number of tokens in the collection"""
    kwargs = {}
    if scheduler_host:
        kwargs["scheduler_host"] = scheduler_host
    else:
        kwargs["local_scheduler"] = True

    if sample_id is not None:
        sample_ids = [sample_id]
    else:
        sample_ids = list(range(num_sample_ids))

    tasks = []
    for sample_id in sample_ids:
        task = ProcessSentenceTransformer(
            input_path=input_path,
            output_path=output_path,
            sample_id=sample_id,
            num_sample_ids=num_sample_ids,
            model_name=model_name,
            cpu_count=cpu_count,
            batch_size=batch_size,
        )
        tasks.append(task)

    luigi.build(tasks, **kwargs)
