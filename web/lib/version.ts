import releasesFile from "../data/releases.json";

export interface Release {
  version: string;
  status: "released" | "unreleased";
  date: string | null;
  important: string[];
  added: string[];
  fixed: string[];
}

/** « 0.2.0 » → [0, 2, 0]. Les suffixes (rc1, dev…) sont ignorés. Illisible → [0, 0, 0]. */
export function parseVersion(v: string): [number, number, number] {
  const m = /^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?/.exec(v ?? "");
  return m ? [Number(m[1]), Number(m[2] ?? 0), Number(m[3] ?? 0)] : [0, 0, 0];
}

export function compareVersions(a: string, b: string): number {
  const pa = parseVersion(a);
  const pb = parseVersion(b);
  for (let i = 0; i < 3; i++) if (pa[i] !== pb[i]) return pa[i] < pb[i] ? -1 : 1;
  return 0;
}

export function allReleases(): Release[] {
  return (releasesFile.releases as Release[]).slice().sort((x, y) => compareVersions(x.version, y.version));
}

/** Dernière version PUBLIÉE (les versions « unreleased » ne sont jamais annoncées aux clients). */
export function latestReleased(override?: string | null): string {
  if (override && /^\d+\.\d+\.\d+$/.test(override.trim())) return override.trim();
  const released = allReleases().filter((r) => r.status === "released");
  return released.length ? released[released.length - 1].version : "0.0.0";
}

/** Notes cumulées : versions strictement après `from`, jusqu'à `latest` incluse (c'est `latest` qui décide de ce qui est annoncé). */
export function notesBetween(from: string, latest: string): Release[] {
  return allReleases().filter((r) => compareVersions(r.version, from) > 0 && compareVersions(r.version, latest) <= 0);
}
