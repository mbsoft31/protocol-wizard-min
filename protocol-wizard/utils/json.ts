
import { Query } from '../types';

// Deep sort object keys recursively to match backend canonicalization
function deepSort(obj: any): any {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(deepSort);
  }
  const sorted: any = {};
  Object.keys(obj)
    .sort()
    .forEach((key) => {
      sorted[key] = deepSort(obj[key]);
    });
  return sorted;
}

export function canonicalJSONStringify(obj: any): string {
  const sorted = deepSort(obj);
  return JSON.stringify(sorted, null, 0);
}

export function prettyJSONStringify(obj: any): string {
  return JSON.stringify(obj, null, 2);
}

export function stripCodeFences(text: string): string {
    return text.replace(/```(json|jsonl)?\s*/g, '').replace(/```\s*$/g, '');
}

export function normalizeAndStringifyJsonl(data: Query[] | string): string {
  if (typeof data === 'string') {
    try {
      // It might be an array in a string
      const parsed = JSON.parse(data);
      if (Array.isArray(parsed)) {
        return parsed.map(item => JSON.stringify(item)).join('\n');
      }
    } catch (e) {
      // Not a valid JSON array string, assume it's already JSONL
      return data;
    }
    return data;
  }
  
  if (Array.isArray(data)) {
    return data.map(item => JSON.stringify(item)).join('\n');
  }
  
  return '';
}
