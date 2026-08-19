.PHONY: help setup merge clean

help:
	@echo "Targets:"
	@echo "  make setup  - install Python dependencies (PyMuPDF, python-pptx, PyYAML)"
	@echo "  make merge  - merge PDFs per order.yaml -> output/merged_pdfs/ + output/output_pptx_import/"
	@echo "  make clean  - remove generated output/ files"

setup:
	pip install -r requirements.txt

merge:
	python3 pdf_to_merger.py

clean:
	rm -rf output/merged_pdfs/* output/output_pptx_import/* temp_images/*
