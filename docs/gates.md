# Gates (cheapest first)
1. Format + lint
2. Type check
3. Unit tests
4. Integration tests
5. AC coverage check (every AC id appears in a test name)
6. Review agent vs spec + ADRs
CI repeats 1-5. Failing gate blocks merge.
