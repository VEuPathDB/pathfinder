/**
 * Reference data fetched from live VEuPathDB APIs.
 *
 * Worker-scoped: fetched once per Playwright worker process.
 * Read-only: tests never mutate this data.
 */

/** Per-site gene data used by journey tests. */
export interface SiteGeneData {
  /** Known gene IDs verified against the live VEuPathDB site. */
  geneIds: string[];
  /** Default organism for GenesByTaxon search on this site. */
  organism: string;
}

export interface SeedData {
  /** Known PlasmoDB gene IDs (malaria drug resistance markers). */
  plasmoGenes: string[];
  /** Known ToxoDB gene IDs (host invasion machinery). */
  toxoGenes: string[];
  /** Default site for most tests. */
  defaultSite: string;
  /** All available sites (fetched from /api/v1/sites). */
  availableSites: string[];
  /** Per-site gene data for journey tests across all 5 databases. */
  siteData: Record<string, SiteGeneData>;
}

/**
 * Fetch reference gene IDs from live VEuPathDB.
 *
 * Uses the PathFinder gene search endpoint which calls real WDK APIs.
 * Falls back to hardcoded known-good IDs if the API is unreachable.
 */
export async function fetchSeedData(baseURL: string): Promise<SeedData> {
  const plasmoGenes = await fetchGeneIds(
    baseURL,
    "plasmodb",
    "chloroquine resistance",
    [
      "PF3D7_0709000", // CRT (chloroquine resistance transporter)
      "PF3D7_1343700", // Kelch13 (artemisinin resistance)
      "PF3D7_0523000", // MDR1 (multidrug resistance)
      "PF3D7_0810800", // DHFR-TS (antifolate resistance)
      "PF3D7_0417200", // DHPS (sulfadoxine resistance)
    ],
  );

  const toxoGenes = await fetchGeneIds(baseURL, "toxodb", "invasion", [
    "TGME49_261080", // MIC2 (micronemal protein)
    "TGME49_233460", // RON4 (rhoptry neck protein)
    "TGME49_300100", // AMA1 (apical membrane antigen)
  ]);

  const tritrypGenes = await fetchGeneIds(baseURL, "tritrypdb", "surface protease", [
    "LmjF.10.0460", // MSP (major surface protease / GP63)
    "LmjF.35.0010", // A2 family (amastigote-specific)
    "LmjF.33.1740", // Cysteine peptidase B
  ]);

  const cryptoGenes = await fetchGeneIds(baseURL, "cryptodb", "oocyst wall", [
    "cgd7_5030", // COWP1 (oocyst wall protein)
    "cgd6_1080", // COWP-domain protein
    "cgd3_920", // GP60 (surface glycoprotein)
  ]);

  const fungiGenes = await fetchGeneIds(baseURL, "fungidb", "glucan synthase", [
    "AFUA_6G12400", // FKS1 (beta-1,3-glucan synthase)
    "AFUA_2G13440", // Chitin synthase
    "AFUA_2G05340", // GEL2 (beta-1,3-glucanosyltransferase)
  ]);

  const sites = await fetchSites(baseURL);

  const siteData: Record<string, SiteGeneData> = {
    plasmodb: {
      geneIds: plasmoGenes,
      organism: "Plasmodium falciparum 3D7",
    },
    toxodb: {
      geneIds: toxoGenes,
      organism: "Toxoplasma gondii ME49",
    },
    tritrypdb: {
      geneIds: tritrypGenes,
      organism: "Leishmania major strain Friedlin",
    },
    cryptodb: {
      geneIds: cryptoGenes,
      organism: "Cryptosporidium parvum Iowa II",
    },
    fungidb: {
      geneIds: fungiGenes,
      organism: "Aspergillus fumigatus Af293",
    },
  };

  return {
    plasmoGenes,
    toxoGenes,
    defaultSite: "veupathdb",
    availableSites: sites,
    siteData,
  };
}

async function fetchGeneIds(
  baseURL: string,
  siteId: string,
  query: string,
  fallback: string[],
): Promise<string[]> {
  try {
    const resp = await fetch(
      `${baseURL}/api/v1/sites/${siteId}/genes/search?q=${encodeURIComponent(query)}&limit=10`,
    );
    if (!resp.ok) return fallback;
    const data = (await resp.json()) as {
      results?: { geneId: string; organism: string }[];
    };
    const ids = (data.results ?? []).map((r) => r.geneId);
    if (ids.length === 0) return fallback;

    // Validate: resolve gene IDs against the site's WDK to ensure they
    // actually belong to this database.  The gene search API may return
    // cross-site results, which would cause WDK enrichment to find 0 genes.
    const resolveResp = await fetch(`${baseURL}/api/v1/sites/${siteId}/genes/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ geneIds: ids }),
    });
    if (!resolveResp.ok) return fallback;
    const resolved = (await resolveResp.json()) as {
      resolved: { geneId: string }[];
    };
    const validIds = resolved.resolved.map((r) => r.geneId);
    return validIds.length >= fallback.length ? validIds : fallback;
  } catch {
    return fallback;
  }
}

async function fetchSites(baseURL: string): Promise<string[]> {
  try {
    const resp = await fetch(`${baseURL}/api/v1/sites`);
    if (!resp.ok) return ["plasmodb", "toxodb", "tritrypdb", "cryptodb", "fungidb"];
    const sites = (await resp.json()) as { id: string }[];
    return sites.map((s) => s.id);
  } catch {
    return ["plasmodb", "toxodb", "tritrypdb", "cryptodb", "fungidb"];
  }
}
