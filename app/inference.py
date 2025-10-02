import hashlib
import time
from typing import List, Tuple


class Embedder:
	def encode(self, texts: List[str], batch_size: int = 64) -> List[List[float]]:
		# Заглушка: возвращаем фиксированный вектор на основе хэша
		embeddings: List[List[float]] = []
		for text in texts:
			h = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
			vec = [((h >> (i * 8)) & 0xFF) / 255.0 for i in range(16)]
			embeddings.append(vec)
		return embeddings


class MultiLabelClassifier:
	def __init__(self, topics: List[str]):
		self.topics = topics

	def predict(self, embeddings: List[List[float]]) -> Tuple[List[List[str]], List[List[float]]]:
		pred_topics: List[List[str]] = []
		pred_probs: List[List[float]] = []
		for emb in embeddings:
			# Простая эвристика по сумме/паритету компонентов
			score = sum(emb)
			chosen = []
			probs = []
			for idx, topic in enumerate(self.topics):
				p = ((score + idx * 0.1) % 1.0)
				if p > 0.6:
					chosen.append(topic)
					probs.append(p)
			# Обеспечим хотя бы одну тему
			if not chosen:
				chosen = [self.topics[int(score * 1000) % len(self.topics)]]
				probs = [0.61]
			pred_topics.append(chosen)
			pred_probs.append(probs)
		return pred_topics, pred_probs


class SentimentModel:
	label_map = ["положительно", "нейтрально", "отрицательно"]

	def predict(self, texts: List[str], topics: List[List[str]]) -> Tuple[List[List[str]], List[List[float]]]:
		all_sents: List[List[str]] = []
		all_probs: List[List[float]] = []
		for text, t_list in zip(texts, topics):
			h = int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16)
			res = []
			probs = []
			for j, _ in enumerate(t_list):
				idx = (h + j) % 3
				res.append(self.label_map[idx])
				probs.append(0.6 + (idx * 0.1))
			all_sents.append(res)
			all_probs.append(probs)
		return all_sents, all_probs


