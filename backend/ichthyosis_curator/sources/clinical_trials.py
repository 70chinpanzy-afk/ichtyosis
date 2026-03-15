"""ClinicalTrials.gov API v2による臨床試験検索"""

import logging
from datetime import datetime, timedelta

import requests

from ichthyosis_curator.schemas import RawArticle

logger = logging.getLogger(__name__)

CTGOV_API_URL = "https://clinicaltrials.gov/api/v2/studies"

SEARCH_TERMS = [
    "ichthyosis",
    "lamellar ichthyosis",
    "congenital ichthyosiform erythroderma",
    "ichthyosis erythroderma",
]


def search_clinical_trials(days_back: int = 30) -> list[RawArticle]:
    """ClinicalTrials.govで最近更新された臨床試験を検索"""
    articles: list[RawArticle] = []
    seen_nct: set[str] = set()

    min_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    max_date = datetime.now().strftime("%Y-%m-%d")

    for term in SEARCH_TERMS:
        params = {
            "query.term": term,
            "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{min_date},{max_date}]",
            "pageSize": 20,
            "format": "json",
        }

        try:
            resp = requests.get(CTGOV_API_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for study in data.get("studies", []):
                protocol = study.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                nct_id = id_module.get("nctId", "")

                if not nct_id or nct_id in seen_nct:
                    continue
                seen_nct.add(nct_id)

                title = id_module.get("officialTitle") or id_module.get("briefTitle", "")
                desc_module = protocol.get("descriptionModule", {})
                abstract = desc_module.get("briefSummary", "")

                status_module = protocol.get("statusModule", {})
                last_update = status_module.get("lastUpdatePostDateStruct", {}).get("date", "")

                articles.append(
                    RawArticle(
                        source="clinical_trials",
                        source_id=nct_id,
                        title=title,
                        abstract=abstract,
                        url=f"https://clinicaltrials.gov/study/{nct_id}",
                        published_date=last_update,
                        language="en",
                    )
                )

        except Exception as e:
            logger.warning(f"ClinicalTrials.gov search failed for '{term}': {e}")
            continue

    logger.info(f"ClinicalTrials.gov: {len(articles)} studies found")
    return articles
