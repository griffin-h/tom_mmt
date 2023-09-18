# TOM MMT
MMT Observatory module for the TOM Toolkit, based on Sam Wyatt's [MMT API interface](https://github.com/swyatt7/mmtapi). Binospec and MMIRS are supported.

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

Add your API keys to the `FACILITIES` dictionary inside `settings.py`:

```python
FACILITIES = {
   ...
    'MMT': {
        'programs': {
            'Binospec': [
                ('3hirty2wocharacterapitoken4ormmt', 'Human-Readable Program Name'),
                ('1notherverylong6exadecimalstring', 'The Name of Another Program'),
                ...
            ],
            'MMIRS': [
                ('3hirty2wocharacterapitoken4ormmt', 'Human-Readable Program Name'),
                ('1notherverylong6exadecimalstring', 'The Name of Another Program'),
                ...
            ],
        },
    },
}
```
Keep in mind that Binospec and MMIRS programs have separate API keys even if they are part of the same proposal.
