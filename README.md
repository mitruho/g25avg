# G25 Averager

### Input formats supported:
1) CSV-like lines:
   SampleName,0.123,0.456,... (25 numbers)
2) Optional whitespace around commas is fine.
3) Blank lines and lines starting with # are ignored.

### Modes:
- simple: average all samples equally
- grouped: average by group prefix (text before first ':', or before first '_' if no ':'),
          then average group means equally (prevents sample-count imbalance)
### Usage
```
python g25_average.py <input_file> --mode <mode> --out <output_file>
```
after which you will be prompted to name the resulting coordinates
