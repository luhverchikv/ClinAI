import faiss, json, numpy as np
from sentence_transformers import SentenceTransformer

class RAGSearch:
    def __init__(self, index_path="data/clinical_protocols.faiss", 
                 meta_path="data/metadata.json",
                 model="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            self.meta = json.load(f)
        self.model = SentenceTransformer(model, device="cpu")
        print(f"✅ База загружена: {self.index.ntotal} документов | RAM: ~5 MB")

    def search(self, query: str, k: int = 3, section_filter: str = None):
        # Векторизуем запрос (без префикса passage, просто текст)
        q_vec = self.model.encode([query], normalize_embeddings=True).astype(np.float32)
        
        # Ищем топ-k+10 на случай фильтров
        dists, idxs = self.index.search(q_vec, k=min(k+10, self.index.ntotal))
        
        results = []
        for i, idx in enumerate(idxs[0]):
            item = self.meta[idx]
            if section_filter and item["metadata"].get("section_type") != section_filter:
                continue
            results.append({
                "score": float(dists[0][i]),
                "text": item["text"],
                "metadata": item["metadata"]
            })
            if len(results) >= k: break
        return results

# Тест
if __name__ == "__main__":
    rag = RAGSearch()
    res = rag.search("Лечение гипертонического криза", k=2, section_filter="treatment_acute")
    for r in res:
        print(f"📊 Score: {r['score']:.3f} | {r['metadata']['icd10_code']}")
        print(r['text'][:150] + "...")

