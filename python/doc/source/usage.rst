Usage
=====

|name| is distributed via BBP Spack packages, and is available at BBP systems as |name| module.

.. code-block::console

    $ module load placement-algorithm

To pin module version, please consider using some specific `BBP archive S/W release <https://bbpteam.epfl.ch/project/spaces/display/BBPHPC/BBP+ARCHIVE+SOFTWARE+MODULES#BBPARCHIVESOFTWAREMODULES-TousetheSpackarchivemodules>`_.

This module brings several commands, some of them to be used for circuit building; and others as auxiliary tools for debugging placement algorithm itself.
We will briefly list them below.

.. tip::

    Under the hood |name| is a Python package.

    Those willing to experiment with development versions can thus install it from BBP devpi server:

    .. code-block:: console

        $ pip install -i https://bbpteam.epfl.ch/repository/devpi/simple/ placement-algorithm[all]

    Please note though that it requires ``mpi4py`` which can be non-trivial to install.

choose-morphologies
-------------------

Choose morphologies using the algorithm described above for all positions in a given nodes file file; and dump output to TSV file like:

::

  0 <morphology-name-1>
  1 <morphology-name-2>

i.e. zero-based cell ID and chosen morphology per line.

All cell IDs from MVD3 would be listed in the output; those where no morphology can be picked (all candidate morphologies get zero score) would have ``N/A`` for morphology name.

Parameters
~~~~~~~~~~

    --mvd3                Path to input MVD3 file [deprecated: use --cells-path instead]
    --cells-path          Path to a file storing cells collection [required]
    --morphdb             Path to MorphDB file [required]
    --atlas               Atlas URL containing the ``[PHx]`` files; ``x`` denote the layer as defined in the placement rules file [required]
    --atlas-cache         Atlas cache folder [optional, default: None]
    --annotations         Path to JSON file with compacted annotations [required]
    --rules               Path to placement rules file [required]
    --segment-type        Segment type to consider (if not specified, consider both) [optional, choices: ['axon', 'dendrite']]
    --alpha               Exponential factor :math:`\alpha` for scores, see above [optional, default: 1.0]
    --scales              Scale(s) to check (scaling factors along the Y axis) [optional, default: None]
    --seed                Random number generator seed [optional, default: 0]
    --output              Path to output TSV file [required]
    --no-mpi              Do not use MPI and run everything on a single core [optional]
    --scores-output-path  Directory path to which the scores for each cell are exported [optional]
    --bias-kind           Kind of bias used to penalize scores of rescaled morphologies [optional, choices: ['uniform', 'linear', 'gaussian'], default: 'linear']
    --no-optional-scores  Trigger to ignore optional rules for morphology choice [optional]


assign-morphologies
-------------------

Write morphologies from TSV list obtained with ``choose-morphologies`` to SONATA.

More in detail:

- read the morphologies from the TSV list created with ``choose-morphologies``,
- apply a random rotation around Y-axis (the principal direction of the morphology) for each cell,
- apply the rotation defined in the atlas orientation field,
- write the result to SONATA file.

By default, the random rotation is a uniform angle distribution between ``-pi`` and ``+pi``.
It can be customized or avoided using the ``--rotations`` parameter described below.

The ``--max-drop-ratio`` option limits the ratio of ``N/A`` morphologies per mtype allowed
in the input TSV list. If not specified, it defaults to zero (i.e., no ``N/A`` allowed).

- If the ratio of ``N/A`` exceeds the limit for any mtype, then the program is terminated and a
  message is printed, indicating the mtypes for which the ``N/A`` ratio exceeded the limit.
- If the ratio of ``N/A`` doesn't exceed the limit for any mtype, then any cell with ``N/A``
  morphology is dropped from the resulting SONATA file.
  If at least one cell is dropped, the resulting file will be re-indexed to preserve continuous
  range of cell IDs.


Parameters
~~~~~~~~~~

      --cells-path CELLS_PATH                Path to a file storing cells collection [required]
      --morph MORPH                          TSV file with morphology list [required]
      --morph-axon MORPH_AXON                TSV file with axon morphology list (for grafting) [default: None]
      --base-morph-dir BASE_MORPH_DIR        Path to base morphology release folder [default: None]
      --atlas ATLAS                          Atlas URL [required]
      --atlas-cache ATLAS_CACHE              Atlas cache folder [default: None]
      --max-drop-ratio MAX_DROP_RATIO        Max drop ratio for any mtype  [default: 0.0]
      --seed SEED                            Random number generator seed [default: 0]
      --out-cells-path OUT_CELLS_PATH        Path to output cells file [required]
      --instantiate                          Write morphology files [default: False]
      --overwrite                            Overwrite output morphology folder [default: False]
      --out-morph-dir OUT_MORPH_DIR          Path to output morphology folder [default: None]
      --out-morph-ext OUT_MORPH_EXT          One or more formats to export morphologies, space separated.
                                             Supported formats: ``h5 swc asc`` [default: ``h5``]
      --max-files-per-dir MAX_FILES_PER_DIR  Maximum files per level for morphology output folder [default: None]
      --rotations ROTATIONS                  Path to the configuration file used for rotations.
                                             If the file is not specified, apply by default
                                             a random rotation with uniform angle distribution around
                                             the Y-axis (the principal direction of the morphology).
                                             [default: None]


dump-profiles
-------------

Debugging utility.

Query m(e)type and layer profile for a list of GIDs; and output the result in JSON lines format.

Parameters
~~~~~~~~~~

    --mvd3            Path to input MVD3 file [required]
    --atlas           Atlas URL [required]
    --atlas-cache     Atlas cache folder [optional, default: None]
    --layer-names     Comma-separated layer names [required]
    --gids            Space-separated list of GID(s) [optional, default: all GIDs]

Example
~~~~~~~

For instance, a call like:

.. code:: bash

  $ dump-profiles \
      --mvd3 <MVD3> \
      --atlas <ATLAS> \
      --layer-names L1,L2,L3,L4,L5,L6 \
      --gids 42 52

can give an output like:

::

  {"L1_0": 1257.1, "L1_1": 1380.0, ..., "L6_0": 0.0, "L6_1": 436.6, "y": 1307.5, "mtype": "L1_DAC", "etype": "cNAC", "gid": 42}
  {"L1_0": 1257.1, "L1_1": 1380.0, ..., "L6_0": 0.0, "L6_1": 436.6, "y": 347.5, "mtype": "L6_UPC", "etype": "cADpyr", "gid": 52}
  ...

The output can be inspected separately or piped directly to ``score-morphologies`` (see below).


score-morphologies
------------------

Debugging utility.

Show each rule score for given position candidate(s) taken from ``stdin``.
Each candidate position is a JSON line similar to ``dump-profile`` output.

Parameters
~~~~~~~~~~

    --morphdb         Path to MorphDB file [required]
    --annotations     Path to JSON file with compacted annotations [required]
    --rules           Path to placement rules file [required]

Example
~~~~~~~

For instance, a call like:

.. code:: bash

  $ score-morphologies \
      --morphdb <MORPHDB> \
      --annotations <ANNOTATIONS> \
      --rules <RULES \
      < '{"L1_0": 1257.1, "L1_1": 1380.0, ..., "L6_0": 0.0, "L6_1": 436.6, "y": 1307.5, "mtype": "L5_TPC:A", "etype": "cADpyr"}' | column -t

can give an output like:

::

  morphology        L1_hard_limit  L5_TPC:A,dendrite,Layer_1  strict  optional  total
  morph-1                   0.732                      0.942   0.732   0.942    0.689
  morph-2 0.688             1.000                      0.688   1.000   0.688    0.688

