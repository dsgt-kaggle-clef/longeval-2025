import luigi
from longeval.collection import RawCollection
from longeval.spark import spark_resource
from pathlib import Path
import typer
from typing_extensions import Annotated

from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, explode, collect_list, expr
from pyspark.sql.types import ArrayType, StringType, IntegerType
from pyspark.ml.feature import Tokenizer, StopWordsRemover, CountVectorizer
from pyspark.ml.clustering import LDA
import numpy as np
import pandas as pd
import os
from pyspark.sql.functions import col, array_max, array_position
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from longeval.collection import ParquetCollection
from pyspark.ml.clustering import DistributedLDAModel
from pyspark.ml.feature import CountVectorizerModel
from sklearn.manifold import MDS
from sklearn.random_projection import GaussianRandomProjection
from pyspark.sql import functions as F


class TrainLDAModel(luigi.Task):
    input_path = luigi.Parameter()
    output_path = luigi.Parameter()
    num_topics = luigi.IntParameter()

    def run(self):
        with spark_resource() as spark:
            spark.sparkContext.setLogLevel("ERROR")

            collection = ParquetCollection(spark, self.input_path)
            # docs = collection.documents.sample(fraction=0.5, seed=42).cache()
            docs = (
                collection.documents
                .filter(F.col("date") == "2023-02")
                .sample(fraction=0.3, seed=42)
                .cache()
            )

            tokenizer = Tokenizer(inputCol="contents", outputCol="words")
            tokenized = tokenizer.transform(docs)
            remover = StopWordsRemover(inputCol="words", outputCol="filtered_words")
            filtered = remover.transform(tokenized)

            vectorizer = CountVectorizer(inputCol="filtered_words", outputCol="features")
            vector_model = vectorizer.fit(filtered)
            vectorized_docs = vector_model.transform(filtered)

            lda = LDA(k=self.num_topics, maxIter=10, featuresCol="features", optimizer="em")
            lda_model = lda.fit(vectorized_docs)

            lda_model.save(os.path.join(self.output_path, "lda_model"))
            vector_model.save(os.path.join(self.output_path, "vector_model"))

            print("LDA model and vectorizer saved successfully.")

    def output(self):
        return luigi.LocalTarget(os.path.join(self.output_path, "lda_model"))


class RunLDAInference(luigi.Task):
    input_path = luigi.Parameter()
    output_path = luigi.Parameter()
    num_topics = luigi.IntParameter()

    def requires(self):
        return TrainLDAModel(input_path=self.input_path, output_path=self.output_path, num_topics=self.num_topics)

    def run(self):
        with spark_resource() as spark:
            lda_model = DistributedLDAModel.load(os.path.join(self.output_path, "lda_model"))
            vector_model = CountVectorizerModel.load(os.path.join(self.output_path, "vector_model"))

            collection = ParquetCollection(spark, self.input_path)
            # docs = collection.documents.sample(fraction=0.5, seed=42).cache()
            docs = (
                collection.documents
                .filter(F.col("date") == "2023-02")
                .sample(fraction=0.3, seed=94)
                .cache()
            )

            tokenized = Tokenizer(inputCol="contents", outputCol="words").transform(docs)
            filtered = StopWordsRemover(inputCol="words", outputCol="filtered_words").transform(tokenized)
            vectorized_docs = vector_model.transform(filtered)

            topics = lda_model.describeTopics(maxTermsPerTopic=100)
            vocab = vector_model.vocabulary
            if not vocab:
                raise ValueError("Vocabulary is empty. Please check the CountVectorizer step.")
            topic_words = {}
            for row in topics.collect():
                topic_index = row.topic
                term_indices = row.termIndices
                terms = [vocab[index] for index in term_indices]
                topic_words[topic_index] = terms
            topic_words_file_path = os.path.join(self.output_path, "topicWords_lda.txt")
            topic_words_df = pd.DataFrame(list(topic_words.items()), columns=["Topic", "Words"])
            topic_words_df.to_csv(topic_words_file_path, index=False)

            topic_distributions = lda_model.transform(vectorized_docs)
            doc_topic_df = topic_distributions.select("docid", "topicDistribution").toPandas()
            doc_topic_array = np.vstack(doc_topic_df["topicDistribution"].apply(lambda v: v.toArray()))
            doc_topic_df['highest_topic'] = np.argmax(doc_topic_array, axis=1)

            topic_probabilities_df = pd.DataFrame(doc_topic_array,
                                                  columns=[f'topic_{i}' for i in range(self.num_topics)])
            result_df = pd.concat([doc_topic_df[['docid']], doc_topic_df[['highest_topic']], topic_probabilities_df],
                                  axis=1)
            result_parquet_path = os.path.join(self.output_path, "docTopicDistribution_lda.parquet")
            result_df_spark = spark.createDataFrame(result_df)
            result_df_spark.write.parquet(result_parquet_path)
            print("Inference completed.")

    def output(self):
        return luigi.LocalTarget(os.path.join(self.output_path, "docTopicDistribution_lda.parquet"))


class PlotResults(luigi.Task):
    input_path = luigi.Parameter()
    output_path = luigi.Parameter()
    num_topics = luigi.IntParameter()

    def requires(self):
        return RunLDAInference(input_path=self.input_path, output_path=self.output_path, num_topics=self.num_topics)

    def run(self):
        with spark_resource() as spark:
            doc_topic_spark_df = spark.read.parquet(os.path.join(self.output_path, "docTopicDistribution_lda.parquet"))
            doc_topic_df = doc_topic_spark_df.toPandas()
            doc_topic_array = doc_topic_df.iloc[:, 2:].values
            dominant_topics = doc_topic_df['highest_topic'].values

            # PCA Plot
            pca = PCA(n_components=2)
            doc_topic_2d_pca = pca.fit_transform(doc_topic_array)
            plt.figure(figsize=(10, 6))
            plt.scatter(doc_topic_2d_pca[:, 0], doc_topic_2d_pca[:, 1], c=dominant_topics, cmap='tab20', alpha=0.6)
            plt.colorbar(label='Topic')
            plt.title('LDA PCA Topic Clusters')
            plt.savefig(os.path.join(self.output_path, 'pca_lda_topics.png'))

            # RP plot
            rp = GaussianRandomProjection(n_components=2, random_state=42)
            doc_topic_2d_rp = rp.fit_transform(doc_topic_array)
            plt.figure(figsize=(10, 6))
            plt.scatter(doc_topic_2d_rp[:, 0], doc_topic_2d_rp[:, 1], c=dominant_topics, cmap='tab20', alpha=0.6)
            plt.colorbar(label='Topic')
            plt.title('LDA RP Topic Clusters')
            plt.savefig(os.path.join(self.output_path, 'rp_lda_topics.png'))

    def output(self):
        return [
            luigi.LocalTarget(os.path.join(self.output_path, 'pca_lda_topics.png')),
            luigi.LocalTarget(os.path.join(self.output_path, 'rp_lda_topics.png'))
        ]


class Workflow(luigi.WrapperTask):
    input_path = luigi.Parameter()
    output_path = luigi.Parameter()
    num_topics = luigi.IntParameter()

    def requires(self):
        return PlotResults(input_path=self.input_path, output_path=self.output_path, num_topics=self.num_topics)


def main(
        num_topics: Annotated[
            int, typer.Argument(help="Number of topics")
        ] = 20,
        input_path: Annotated[
            str, typer.Argument(help="Input root directory")
        ] = "/mnt/data/longeval",
        output_path: Annotated[
            str, typer.Argument(help="Output root directory")
        ] = "/mnt/data/longeval",
        scheduler_host: Annotated[str, typer.Argument(help="Scheduler host")] = None,
):
    """Convert raw data to parquet"""

    kwargs = {}
    if scheduler_host:
        kwargs["scheduler_host"] = scheduler_host
    else:
        kwargs["local_scheduler"] = True

    luigi.build(
        [Workflow(
            num_topics=num_topics,
            input_path=input_path,
            output_path=output_path
        )],
        **kwargs,
    )