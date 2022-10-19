# TOM MMT
MMT Observatory module for the TOM Toolkit, based on Sam Wyatt's [MMT API interface](https://github.com/swyatt7/mmtapi).

**Currently only Binospec is supported.** We hope to support MMIRS soon.

# Installation and Setup
Install this module into your TOM environment:

```shell
pip install tom-mmt
```

Add `tom_mmt.mmt.MMTFacility` to the `TOM_FACILITY_CLASSES` in your TOM's
`settings.py`:
```python
TOM_FACILITY_CLASSES = [
    'tom_observations.facilities.lco.LCOFacility',
    ...
    'tom_mmt.mmt.MMTFacility',
]
```

Add your API key (or a reference to the environment variable) to the `FACILITIES` dictionary inside `settings.py`:

```python
FACILITIES = {
   ...
    'MMT': {
        'api_key': os.getenv('MMT_API_KEY', MMT_API_KEY),
    }
}
```
