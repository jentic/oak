## Pass 1 — field_presence
- Fixed: get__articlesearch.json — added top-level `status` (string) to 200 response schema; real API returns `"OK"`
- Fixed: get__articlesearch.json — added top-level `copyright` (string) to 200 response schema; real API returns attribution string
- Fixed: get__articlesearch.json — renamed `response.meta` to `response.metadata`; real API consistently returns `metadata`, not `meta`
- Fixed: get__articlesearch.json — added `headline.print_headline` (string) to Doc headline schema
- Fixed: get__articlesearch.json — added `multimedia.credit` (string) to multimedia items schema
- Fixed: get__articlesearch.json — added `multimedia.default` (object with url/height/width) to multimedia items schema
- Fixed: get__articlesearch.json — added `multimedia.thumbnail` (object with url/height/width) to multimedia items schema
- Fixed: get__articlesearch.json — added `print_section` (string) to Doc schema
- Fixed: get__articlesearch.json — added `uri` (string) to Doc schema; real API returns NYT internal URI e.g. `nyt://article/...`

## Pass 3 — request_params
- Fixed: get__articlesearch.json — removed `maximum: 10` from `page` parameter schema; real API accepts any page value (tested page=11 and page=100, both return 200 with valid results). The constraint was incorrect and would cause spec-compliant clients to reject valid high-page requests.

## Pass 2 — field_types
- Fixed: get__articlesearch.json — changed `keywords` from object to array of objects; real API returns an array of keyword objects
- Fixed: get__articlesearch.json — changed `keywords[].rank` from string to integer; real API returns integers (1, 2, 3, ...)
- Fixed: get__articlesearch.json — changed `multimedia` from array of flat objects to single object with caption/credit/default/thumbnail; real API returns a single multimedia object per article
- Fixed: get__articlesearch.json — changed `word_count` from string to integer; real API returns integers (e.g. 1184)
