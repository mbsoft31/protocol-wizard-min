
import Ajv from 'ajv';
import { PROTOCOL_SCHEMA } from '../constants';
import { Protocol } from '../types';

const ajv = new Ajv({ allErrors: true });
const validate = ajv.compile(PROTOCOL_SCHEMA);

export function validateProtocol(protocol: Protocol | object | null): { isValid: boolean; errors: typeof validate.errors } {
  if (!protocol) {
    return { isValid: false, errors: [{ message: "Protocol data is missing." }] as any };
  }
  const isValid = validate(protocol);
  return {
    isValid: !!isValid,
    errors: validate.errors || [],
  };
}
