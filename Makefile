draft:
	python protocol_wizard.py draft --subject-file subject.example.txt --outdir outputs

refine:
	python protocol_wizard.py refine --protocol-draft outputs/protocol_draft.json --outdir outputs

queries:
	python protocol_wizard.py queries --protocol-json outputs/protocol_draft.json --out-path outputs/queries_draft.jsonl

freeze:
	python protocol_wizard.py freeze --protocol-json outputs/protocol_draft.json --refinements-json outputs/refinements.json --outdir frozen

api:
	uvicorn server.main:app --reload --port 8000

test:
	pytest -q
