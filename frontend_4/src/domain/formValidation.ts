const NAME_CONNECTORS = new Set(["-", "'", "’"]);

export function normalizeSingleLineText(value: string): string {
  return value.trim().replace(/\s+/g, " ");
}

export function isRequiredText(value: string): boolean {
  return normalizeSingleLineText(value).length > 0;
}

function isValidNameToken(token: string): boolean {
  if (!token) return false;
  const characters = Array.from(token);
  if (NAME_CONNECTORS.has(characters[0] ?? "") || NAME_CONNECTORS.has(characters.at(-1) ?? "")) {
    return false;
  }

  let previousWasConnector = false;
  for (const character of characters) {
    if (NAME_CONNECTORS.has(character)) {
      if (previousWasConnector) return false;
      previousWasConnector = true;
      continue;
    }
    if (!/^\p{L}$/u.test(character)) return false;
    previousWasConnector = false;
  }
  return true;
}

export function isValidProperName(value: string): boolean {
  const clean = normalizeSingleLineText(value);
  if (!clean) return false;
  return clean.split(" ").every(isValidNameToken);
}
