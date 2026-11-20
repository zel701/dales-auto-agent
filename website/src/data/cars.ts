// Toyota US lineup — grade-level catalog generated from the toyota.com
// configurator. Regenerate with:
//   python3 website/scripts/scrape-toyota-configurator.py   (refresh raw dump)
//   python3 website/scripts/generate-toyota-catalog.py      (rebuild catalog)
// Colors are per-grade: not every grade offers every color, so color options
// must always be derived from the selected trims via getColors().

import catalogJson from "./toyota-catalog.json";

export type ColorOption = {
  name: string;
  hex: string | null;
  extraCost: boolean;
  msrp: number;
};

/** A color plus which of the queried grades actually offer it. */
export type GradeColorOption = ColorOption & { grades: string[] };

type CatalogModel = {
  seriesId: string;
  year: number;
  grades: Record<string, { colors: ColorOption[] }>;
};

const catalog = catalogJson as unknown as {
  generatedAt: string;
  models: Record<string, CatalogModel>;
};

export const toyotaModels = catalog.models;

export const models = Object.keys(toyotaModels);

export function getTrims(model: string): string[] {
  return Object.keys(toyotaModels[model]?.grades ?? {});
}

/**
 * Colors available across the given trims (grades) of a model, deduped by
 * name, each annotated with the subset of `trims` that offers it. With no
 * trims given, returns the union across all of the model's grades.
 */
export function getColors(model: string, trims: string[] = []): GradeColorOption[] {
  const m = toyotaModels[model];
  if (!m) return [];
  const selected = trims.length
    ? trims.filter((t) => m.grades[t])
    : Object.keys(m.grades);

  const byName = new Map<string, GradeColorOption>();
  for (const grade of selected) {
    for (const color of m.grades[grade].colors) {
      const existing = byName.get(color.name);
      if (existing) existing.grades.push(grade);
      else byName.set(color.name, { ...color, grades: [grade] });
    }
  }
  return [...byName.values()];
}

export const comingSoonBrands = [
  "Honda",
  "Ford",
  "BMW",
  "Mercedes-Benz",
  "Chevrolet",
  "Hyundai",
  "Kia",
  "Nissan",
  "Subaru",
  "Volkswagen",
];

export const radiusOptions = [
  { label: "50 miles", value: "50" },
  { label: "100 miles", value: "100" },
  { label: "200 miles", value: "200" },
];
