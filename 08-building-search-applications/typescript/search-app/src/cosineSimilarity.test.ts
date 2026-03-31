/**
 * Unit tests for the cosineSimilarity function in main.ts.
 *
 * Azure OpenAI and dotenv are mocked so no API credentials are needed.
 * Because main() is called at module load time we provide enough structure
 * on the mock to prevent runtime errors in that call path.
 */

import { describe, expect, it, vi } from "vitest";

vi.mock("@azure/openai", () => ({
  AzureKeyCredential: vi.fn(),
  OpenAIClient: vi.fn(() => ({
    getEmbeddings: vi.fn().mockResolvedValue({
      data: [{ embedding: [1, 0, 0] }, { embedding: [0, 1, 0] }, { embedding: [0, 0, 1] }],
    }),
  })),
}));

vi.mock("dotenv", () => ({ config: vi.fn() }));

const { cosineSimilarity } = await import("./main");

// ── basic geometry ─────────────────────────────────────────────────────────────

describe("cosineSimilarity – basic geometry", () => {
  it("returns 1 for two identical vectors", () => {
    expect(cosineSimilarity([1, 0, 0], [1, 0, 0])).toBeCloseTo(1.0);
  });

  it("returns 0 for two orthogonal vectors", () => {
    expect(cosineSimilarity([1, 0], [0, 1])).toBeCloseTo(0.0);
  });

  it("returns -1 for two opposing vectors", () => {
    expect(cosineSimilarity([1, 0], [-1, 0])).toBeCloseTo(-1.0);
  });

  it("returns 0.5 for 60-degree angle vectors", () => {
    // a = [1,1,0], b = [1,0,1] → dot=1, |a|=|b|=√2 → cos = 1/2
    expect(cosineSimilarity([1, 1, 0], [1, 0, 1])).toBeCloseTo(0.5);
  });

  it("is commutative", () => {
    const a = [1, 2, 3];
    const b = [4, 5, 6];
    expect(cosineSimilarity(a, b)).toBeCloseTo(cosineSimilarity(b, a));
  });

  it("returns 1 for scaled versions of the same vector", () => {
    expect(cosineSimilarity([1, 2, 3], [2, 4, 6])).toBeCloseTo(1.0);
  });
});

// ── error conditions ───────────────────────────────────────────────────────────

describe("cosineSimilarity – error conditions", () => {
  it("throws when vectors have different dimensions", () => {
    expect(() => cosineSimilarity([1, 0], [1, 0, 0])).toThrow();
  });

  it("throws when the first vector has zero magnitude", () => {
    expect(() => cosineSimilarity([0, 0], [1, 0])).toThrow();
  });

  it("throws when the second vector has zero magnitude", () => {
    expect(() => cosineSimilarity([1, 0], [0, 0])).toThrow();
  });
});
