// Runtime validation placeholders.
// TODO: Replace lightweight checks with Zod schemas when frontend package is wired.

export function assertNonEmptyString(value: unknown, fieldName: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid ${fieldName}: expected non-empty string`);
  }
  return value;
}

export function assertFiniteNumber(value: unknown, fieldName: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Invalid ${fieldName}: expected finite number`);
  }
  return value;
}
