
import { Query } from '../types';

export function canonicalJSONStringify(obj: any): string {
  return JSON.stringify(obj, Object.keys(obj).sort(), 0).replace(/\s/g, "");
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
