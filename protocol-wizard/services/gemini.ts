
import { GoogleGenAI } from '@google/genai';
import { Protocol, Refinements, Query } from '../types';
import {
  DRAFT_PROMPT_TEMPLATE,
  REFINE_PROMPT_TEMPLATE,
  QUERIES_PROMPT_TEMPLATE,
  DRAFT_FALLBACK,
  REFINE_FALLBACK,
} from '../constants';
import { stripCodeFences } from '../utils/json';

interface GeminiResult<T> {
  data: T;
  fromFallback: boolean;
}

const getApiKey = (uiApiKey: string): string | null => {
  const envKey = process.env.VITE_GOOGLE_API_KEY;
  return envKey || uiApiKey || null;
};

const cleanJsonString = (text: string): string => {
  return stripCodeFences(text).trim();
};

export async function generateDraftProtocol(
  subject: string,
  uiApiKey: string,
  modelName: string
): Promise<GeminiResult<Protocol>> {
  const apiKey = getApiKey(uiApiKey);
  if (!apiKey) {
    console.warn('No API key found. Using fallback for draft protocol.');
    return { data: DRAFT_FALLBACK, fromFallback: true };
  }

  try {
    const ai = new GoogleGenAI({ apiKey });
    const prompt = DRAFT_PROMPT_TEMPLATE.replace('{subject_text}', subject);
    
    const response = await ai.models.generateContent({
        model: modelName,
        contents: prompt
    });

    const jsonString = cleanJsonString(response.text);
    const protocol = JSON.parse(jsonString) as Protocol;
    return { data: protocol, fromFallback: false };
  } catch (error) {
    console.error('Error generating draft protocol:', error);
    return { data: DRAFT_FALLBACK, fromFallback: true };
  }
}

export async function generateRefinements(
  protocol: Protocol,
  uiApiKey: string,
  modelName: string
): Promise<GeminiResult<Refinements>> {
  const apiKey = getApiKey(uiApiKey);
  if (!apiKey) {
    console.warn('No API key found. Using fallback for refinements.');
    return { data: REFINE_FALLBACK, fromFallback: true };
  }

  try {
    const ai = new GoogleGenAI({ apiKey });
    const protocolJson = JSON.stringify(protocol, null, 2);
    const prompt = REFINE_PROMPT_TEMPLATE.replace('{protocol_json}', protocolJson);

    const response = await ai.models.generateContent({
        model: modelName,
        contents: prompt
    });

    const jsonString = cleanJsonString(response.text);
    const refinements = JSON.parse(jsonString) as Refinements;
    return { data: refinements, fromFallback: false };
  } catch (error) {
    console.error('Error generating refinements:', error);
    return { data: REFINE_FALLBACK, fromFallback: true };
  }
}

export async function generateQueries(
  protocol: Protocol,
  uiApiKey: string,
  modelName: string
): Promise<GeminiResult<Query[]>> {
  const apiKey = getApiKey(uiApiKey);
  if (!apiKey) {
    console.warn('No API key found. Using fallback for queries (empty).');
    return { data: [], fromFallback: true };
  }

  try {
    const ai = new GoogleGenAI({ apiKey });
    const protocolJson = JSON.stringify(protocol, null, 2);
    const prompt = QUERIES_PROMPT_TEMPLATE.replace('{protocol_json}', protocolJson);
    
    const response = await ai.models.generateContent({
        model: modelName,
        contents: prompt
    });
    
    const jsonlString = cleanJsonString(response.text);
    const queries = jsonlString
      .split('\n')
      .filter(line => line.trim() !== '')
      .map(line => JSON.parse(line)) as Query[];
    return { data: queries, fromFallback: false };
  } catch (error) {
    console.error('Error generating queries:', error);
    return { data: [], fromFallback: true };
  }
}
