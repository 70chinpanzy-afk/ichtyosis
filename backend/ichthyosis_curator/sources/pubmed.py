"""PubMed E-utilities APIによる医学論文検索"""

import time
import logging
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import requests

from ichthyosis_curator.schemas import RawArticle

logger = logging.getLogger(__name__)

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

# 魚鱗癬紅皮症 直接関連 + アトピー等の類似疾患
SEARCH_QUERIES = [
    # 魚鱗癬紅皮症 直接
    '("ichthyosis"[Title/Abstract] OR "erythroderma"[Title/Abstract]) AND ("treatment" OR "therapy" OR "drug")',
    '"lamellar ichthyosis" OR "congenital ichthyosiform erythroderma"',
    '"ichthyosis" AND ("gene therapy" OR "TGM1" OR "ABCA12" OR "ALOX12B")',
    '"ichthyosis" AND ("retinoid" OR "emollient" OR "topical")',
    # 類似疾患からの知見（皮膚バリア・アトピー関連）
    '"skin barrier" AND ("ceramide" OR "repair") AND ("ichthyosis" OR "atopic dermatitis")',
    '"JAK inhibitor" AND ("skin" OR "dermatitis") AND "treatment"',
    '"orphan drug" AND ("skin disease" OR "ichthyosis")',
]


def search_pubmed(email: str, days_back: int = 7, max_results: int = 50) -> list[str]:
    """PubMedで最近の論文を検索し、PMIDリストを返す"""
    all_pmids: set[str] = set()

    for query in SEARCH_QUERIES:
        params = {
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "reldate": days_back,
            "datetype": "edat",
            "retmode": "json",
            "email": email,
        }

        try:
            resp = requests.get(ESEARCH_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
            all_pmids.update(pmids)
            logger.debug(f"PubMed query '{query[:50]}...' -> {len(pmids)} results")
        except Exception as e:
            logger.warning(f"PubMed search failed for query '{query[:50]}...': {e}")
            continue

        time.sleep(0.35)  # NCBI rate limit: max 3 req/sec

    logger.info(f"PubMed: {len(all_pmids)} unique PMIDs found")
    return list(all_pmids)


def fetch_pubmed_articles(pmids: list[str], email: str) -> list[RawArticle]:
    """PMIDリストからフル記事メタデータを取得"""
    if not pmids:
        return []

    articles: list[RawArticle] = []

    # efetchは最大200件ずつ
    for i in range(0, len(pmids), 200):
        batch = pmids[i : i + 200]
        params = {
            "db": "pubmed",
            "id": ",".join(batch),
            "retmode": "xml",
            "email": email,
        }

        try:
            resp = requests.get(EFETCH_URL, params=params, timeout=60)
            resp.raise_for_status()
            articles.extend(_parse_pubmed_xml(resp.text))
        except Exception as e:
            logger.warning(f"PubMed fetch failed for batch {i}: {e}")
            continue

        time.sleep(0.35)

    return articles


def _parse_pubmed_xml(xml_text: str) -> list[RawArticle]:
    """PubMed XML応答をRawArticleに変換"""
    articles: list[RawArticle] = []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        logger.error(f"PubMed XML parse error: {e}")
        return articles

    for article_elem in root.findall(".//PubmedArticle"):
        try:
            medline = article_elem.find(".//MedlineCitation")
            if medline is None:
                continue

            pmid_elem = medline.find("PMID")
            pmid = pmid_elem.text if pmid_elem is not None else ""

            article_node = medline.find("Article")
            if article_node is None:
                continue

            title_elem = article_node.find("ArticleTitle")
            title = title_elem.text if title_elem is not None else ""
            if not title:
                continue

            # Abstract
            abstract_parts = []
            for abs_text in article_node.findall(".//AbstractText"):
                if abs_text.text:
                    label = abs_text.get("Label", "")
                    prefix = f"{label}: " if label else ""
                    abstract_parts.append(f"{prefix}{abs_text.text}")
            abstract = " ".join(abstract_parts)

            # Authors
            authors = []
            for author in article_node.findall(".//Author"):
                last = author.find("LastName")
                first = author.find("ForeName")
                if last is not None and last.text:
                    name = last.text
                    if first is not None and first.text:
                        name = f"{last.text} {first.text}"
                    authors.append(name)

            # Published date
            pub_date_elem = article_node.find(".//PubDate")
            pub_date = ""
            if pub_date_elem is not None:
                year = pub_date_elem.find("Year")
                month = pub_date_elem.find("Month")
                day = pub_date_elem.find("Day")
                parts = []
                if year is not None and year.text:
                    parts.append(year.text)
                if month is not None and month.text:
                    parts.append(month.text)
                if day is not None and day.text:
                    parts.append(day.text)
                pub_date = " ".join(parts)

            # Language
            lang_elem = article_node.find("Language")
            language = lang_elem.text if lang_elem is not None else "en"

            articles.append(
                RawArticle(
                    source="pubmed",
                    source_id=pmid,
                    title=title,
                    abstract=abstract,
                    authors=authors[:5],  # 最大5名
                    url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    published_date=pub_date,
                    language=language,
                )
            )
        except Exception as e:
            logger.warning(f"PubMed article parse error: {e}")
            continue

    return articles


def get_pubmed_articles(email: str, days_back: int = 7) -> list[RawArticle]:
    """PubMedから関連論文を検索・取得"""
    pmids = search_pubmed(email, days_back)
    return fetch_pubmed_articles(pmids, email)
