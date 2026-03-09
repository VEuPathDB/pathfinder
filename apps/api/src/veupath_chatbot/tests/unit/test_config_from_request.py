"""Test config_from_request passes all fields through."""

from veupath_chatbot.transport.http.routers.experiments._config import (
    config_from_request,
)
from veupath_chatbot.transport.http.schemas.experiments import (
    CreateExperimentRequest,
)


def test_config_from_request_passes_target_gene_ids():
    req = CreateExperimentRequest(
        siteId="PlasmoDB",
        recordType="gene",
        searchName="GenesByTaxon",
        parameters={},
        positiveControls=["G1"],
        negativeControls=[],
        controlsSearchName="GeneByLocusTag",
        controlsParamName="ds_gene_ids",
        targetGeneIds=["G1", "G2", "G3"],
    )
    config = config_from_request(req)
    assert config.target_gene_ids == ["G1", "G2", "G3"]


def test_config_from_request_target_gene_ids_default_none():
    req = CreateExperimentRequest(
        siteId="PlasmoDB",
        recordType="gene",
        searchName="GenesByTaxon",
        parameters={},
        positiveControls=["G1"],
        negativeControls=[],
        controlsSearchName="GeneByLocusTag",
        controlsParamName="ds_gene_ids",
    )
    config = config_from_request(req)
    assert config.target_gene_ids is None
