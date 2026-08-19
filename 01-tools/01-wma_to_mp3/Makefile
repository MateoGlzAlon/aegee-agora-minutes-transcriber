.PHONY: help convert clean

help:
	@echo "Targets:"
	@echo "  make convert  - convert input/*.wma -> output/*.mp3 (requires ffmpeg)"
	@echo "  make clean    - remove converted files from output/"

convert:
	./process_audio.sh

clean:
	rm -f output/*.mp3
