#!/bin/bash
# Generate TypeScript types from JSON Schema

set -e

echo "🔧 Generating TypeScript types from Protocol JSON Schema..."

# Check if json-schema-to-typescript is installed
if ! command -v json2ts &> /dev/null; then
    echo "❌ json-schema-to-typescript not found"
    echo "📦 Installing globally..."
    npm install -g json-schema-to-typescript
fi

# Check if schema file exists
if [ ! -f "schemas/protocol.schema.json" ]; then
    echo "❌ Schema file not found: schemas/protocol.schema.json"
    exit 1
fi

# Generate types
OUTPUT_DIR="generated"
OUTPUT_FILE="$OUTPUT_DIR/protocol-types.ts"

mkdir -p "$OUTPUT_DIR"

echo "📝 Generating types..."
json2ts schemas/protocol.schema.json > "$OUTPUT_FILE"

echo "✅ TypeScript types generated: $OUTPUT_FILE"
echo ""
echo "Usage in your frontend:"
echo ""
echo "  import { Protocol, Keywords, Screening } from './generated/protocol-types';"
echo ""
echo "  const protocol: Protocol = {"
echo "    research_questions: ['...'],"
echo "    keywords: {...},"
echo "    // ..."
echo "  };"
echo ""

# Optionally validate the generated file
if command -v tsc &> /dev/null; then
    echo "🔍 Validating generated TypeScript..."
    tsc --noEmit "$OUTPUT_FILE" 2>/dev/null && echo "✅ Types are valid!" || echo "⚠️  Type validation warnings (may be ignorable)"
fi

echo ""
echo "💡 Tip: Add this script to your CI/CD pipeline to keep types in sync!"