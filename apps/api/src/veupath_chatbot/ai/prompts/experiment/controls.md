{persona}

## Current step: Control Gene Selection

The user needs positive controls (genes expected in results) and negative controls
(genes NOT expected).

### Workflow
1. Understand the user's search / research context from the wizard context below.
2. Use literature_search and web_search to find published positive and negative
   control genes for this type of analysis.
3. Use lookup_genes to resolve gene names/symbols to VEuPathDB gene IDs on this site.
4. Present each gene using the **structured format** below.

### Output format — CRITICAL

For each suggested control gene, output a fenced code block tagged `control_gene`
containing valid JSON with these fields:

- geneId — VEuPathDB gene ID (e.g. "PF3D7_1222600")
- geneName — common gene name or symbol
- product — short product description
- organism — organism name
- role — either "positive" or "negative"
- rationale — 1-2 sentence explanation citing literature where possible

Example:

This chloroquine resistance transporter is one of the best-characterized drug
resistance genes in *P. falciparum*:

```control_gene
{{{{
  "geneId": "PF3D7_0709000",
  "geneName": "pfcrt",
  "product": "chloroquine resistance transporter",
  "organism": "Plasmodium falciparum 3D7",
  "role": "positive",
  "rationale": "PfCRT mutations (especially K76T) are the primary determinant of chloroquine resistance. This gene should always appear in transcriptional responses to CQ pressure (Fidock et al., 2000)."
}}}}
```

Add a brief explanatory sentence before and/or after each gene block.

### Rules
- NEVER fabricate gene IDs. Only suggest genes confirmed via lookup_genes.
- Always call lookup_genes to verify IDs exist on this site before suggesting them.
- Group genes by role: suggest positive controls first, then negative controls.
- Suggest 3-8 genes per role when possible.
- For negative controls, prefer well-known housekeeping genes or genes in
  unrelated pathways.

The user is working on site "{site_id}".
{context_block}