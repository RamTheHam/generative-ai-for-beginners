/**
 * Unit tests for the getCurrentWeatherFunction schema in main.ts.
 *
 * The schema is passed directly to the Azure OpenAI function-calling API.
 * Validating its structure here catches regressions (wrong field names, missing
 * required properties) before they reach the API and fail silently.
 */

import { describe, expect, it, vi } from "vitest";

vi.mock("@azure/openai", () => ({
  AzureKeyCredential: vi.fn(),
  OpenAIClient: vi.fn(() => ({
    getChatCompletions: vi.fn().mockResolvedValue({ choices: [] }),
  })),
}));

vi.mock("axios", () => ({ default: { get: vi.fn().mockResolvedValue({ data: {} }) } }));

vi.mock("dotenv", () => ({ config: vi.fn() }));

const { getCurrentWeatherFunction } = await import("./main");

// ── schema structure ───────────────────────────────────────────────────────────

describe("getCurrentWeatherFunction schema", () => {
  it("has the name 'findWeather'", () => {
    expect(getCurrentWeatherFunction.name).toBe("findWeather");
  });

  it("has a non-empty description", () => {
    expect(getCurrentWeatherFunction.description).toBeTruthy();
    expect(typeof getCurrentWeatherFunction.description).toBe("string");
  });

  it("declares 'object' as the root parameter type", () => {
    expect(getCurrentWeatherFunction.parameters.type).toBe("object");
  });

  it("defines a 'location' property", () => {
    expect(getCurrentWeatherFunction.parameters.properties.location).toBeDefined();
  });

  it("defines 'location' as a string", () => {
    expect(getCurrentWeatherFunction.parameters.properties.location.type).toBe("string");
  });

  it("defines a 'unit' property", () => {
    expect(getCurrentWeatherFunction.parameters.properties.unit).toBeDefined();
  });

  it("restricts 'unit' to Celsius ('C') and Fahrenheit ('F')", () => {
    const { enum: units } = getCurrentWeatherFunction.parameters.properties.unit;
    expect(units).toContain("C");
    expect(units).toContain("F");
    expect(units).toHaveLength(2);
  });

  it("marks 'location' as a required parameter", () => {
    expect(getCurrentWeatherFunction.parameters.required).toContain("location");
  });
});
