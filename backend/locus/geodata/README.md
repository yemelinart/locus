# Offline place reference

Derived from [GeoNames](https://www.geonames.org/), downloaded 2026-09-22:
cities15000.zip (populated places), admin1CodesASCII.txt, and ADM1 records
from UA.zip. GeoNames data is licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Changes: selected
identifiers, names/aliases, country and first-level region; omitted coordinates,
population and other attributes; serialized and compressed for local use.

English, Russian and Ukrainian country names derive from Unicode CLDR, under
the accompanying **UNICODE-LICENSE.txt**. Names are references, not verified
evidence about a person. There is no runtime network call to these providers.

Rebuild with scripts/build_places.py; the manifest records input hashes.
The snapshot has 34,146 records. Coverage is incomplete, particularly for small
places. Alternate names may be historic or ambiguous. Unresolved qualifiers
must not be dropped. Only Ukrainian regions have extra multilingual aliases;
other regional names currently come from GeoNames' English/ASCII export.
