.. |name| replace:: ``placement-algorithm``

Welcome to placement-algorithm's documentation!
===============================================

Overview
========

|name| is an implementation of the algorithm for picking morphologies for given cell positions, which aims to match a set of constraints prescribed by *placement rules*.

Methodology
===========

Candidate pool
--------------

For each cell in MVD3 we obtain its position :math:`y` along its "principal direction" :math:`Y` (for instance, for cortical regions it is the direction towards pia); as well as all layer boundaries along :math:`Y`.
This gives us cell position `profile`.
Please refer to :ref:`Atlas <ref-data-atlas>` section for the details where do these numbers come from.

To reduce computation, we coarsen these profiles, specifying their `resolution`.
Note there is trade-off between performance and precision; 10 um resolution works fine in practice.

Cells are then grouped by (`layer`, `mtype`, `etype`, `profile`), and joined to the morphology database using (`layer`, `mtype`, `etype`) as the join key.

Each (`morphology`, `profile`) pair from the resulting `candidate pool` is then given a score using the algorithm described in the detail in the next section.

Once each (`morphology`, `profile`) pair is scored, we group them *by profile*. Using scores as probability weights, we pick a morphology for every cell from the corresponding profile group (sampling with replacement). If no morphology gets a positive score at the given profile, all the corresponding cell positions are dropped.

The choice of morphologies can be tuned with :math:`\alpha` parameter, which specifies the exponential factor for each score. I.e., instead of using score :math:`S` as probability weights, one can use :math:`S^\alpha`. Using :math:`\alpha > 1` thus gives more preference to high scorers.


Calculating a placement score
-----------------------------

For each location we assign the morphology a score that reflects to what degree the applicable placement rules are fulfilled, if the morphology was placed at that location. This score is a real number from :math:`[0.0, 1.0]`, with :math:`0.0` indicating that a placement is impossible and :math:`1.0` indicating that all restrictions are fully met.

The set of rules applicable for each type is defined in :ref:`placement rules <ref-data-rules>` file.

Each morphology is :ref:`annotated <ref-data-annotations>` accordingly to pre-calculate Y-intervals for each region of interest (apical tuft, for instance).

Scores are first calculated for each separate rule and then combined to a total score.
If annotation corresponding to the rule is missing in morphology annotations, this rule is ignored when calculating the scores.

We distinguish two types of rules: *strict* ones and *optional* ones.
We aggregate scores for those differently, penalizing low *strict* score heavier than low *optional* score (see below).

In the following descriptions we will denote :math:`Y`-interval for a given morphology :math:`M` at a given position :math:`p` according to morphology annotation with :math:`(a^\uparrow, a^\downarrow)`; and :math:`Y`-interval prescribed by a placement rule with :math:`(r^\uparrow, r^\downarrow)`.


Common elements
~~~~~~~~~~~~~~~

Each rule in the :ref:`placement rules <ref-data-rules>` file is grouped into a ``mtype_rule_set`` for a given *mtype*. Example:

.. code-block:: xml

    <mtype_rule_set mtype="L2_TPC:A">
      <rule id="L2_TPC:A, dendrite, Layer_1"  type="region_target" segment_type="dendrite" y_min_layer="L1" y_min_fraction="0.00" y_max_layer="L1" y_max_fraction="1.00" />
      <rule id="L2_TPC:A, axon, Layer_5"  type="region_target" segment_type="axon" y_min_layer="L1" y_min_fraction="0.00" y_max_layer="L5" y_max_fraction="1.00" />
    </mtype_rule_set>

Each rule has the following common elements:

- ``id`` is an unique string label of a rule
- ``type`` specifies the *type* of the rule, as described below; must be  ``below``, ``region_target`` or ``region_occupy``.
- ``segment-type`` [likely deprecated] describes the segment the rule applies to; must be ``axon`` or ``dendrite``

Strict rules
~~~~~~~~~~~~

As of now we have a single *strict* rule type named ``below``.
It prescribes that morphology should stay below certain Y-limit :math:`r^\uparrow`.
Thus we also address these rules as *hard limit* rules.

below
^^^^^

Despite the name "hard limit", we allow a small error margin: a base score of :math:`1.0` is reduced for each :math:`\mu` um exceeding the limit until reaching `0.0` for :math:`\mu=30` um.

.. math::

    L = \max\left(\min\left(\frac{r^\uparrow - a^\uparrow + 30}{30}, 1\right),0\right)

In placement rules file these rules are encoded with ``<rule type=below>`` elements:

.. code-block:: xml

    <rule id="L1_hard_limit" type="below" segment_type="dendrite" y_layer="1" y_fraction="1.0"/>

- ``y_layer``, ``y_fraction`` specify layer ID (string) and relative position in the layer (:math:`0.0` to :math:`1.0`) corresponding to the upper limit :math:`r^\uparrow`
- ``segment_type`` attribute is not used at the moment

Optional rules
~~~~~~~~~~~~~~

As of now we have two rules of these type: ``region_target`` and ``region_occupy``.

These are rules of the type where an interval in the layer structure (for example upper half of layer 5) has to be aligned with an (vertical) interval in the structure of the morphology (for example: the apical tuft). Thus we also address these rules as *interval overlap* rules.

region_target
^^^^^^^^^^^^^

Assuming :math:`(a^\uparrow, a^\downarrow)` is :math:`Y`-interval for a given morphology :math:`M` at a given position :math:`p` according to morphology annotation; and :math:`(r^\uparrow, r^\downarrow)` is :math:`Y`-interval prescribed by a placement rule, we calculate the overlap between the two:

.. math::

    I = \max{\left(\frac{\min\left(a^\uparrow, r^\uparrow\right) - \max\left(a^\downarrow, r^\downarrow\right)}{\min\left(a^\uparrow - a^\downarrow, r^\uparrow - r^\downarrow\right)}, 0\right)}

:math:`I` varies from :math:`0.0` (no overlap) to :math:`1.0` (max possible overlap, i.e. one of the intervals contains another).

In placement rules file these rules are encoded with ``<rule type=region_target>`` elements:

.. code-block:: xml

    <rule id="dendrite, Layer_1"  type="region_target" segment_type="dendrite" y_min_layer="1" y_min_fraction="0.00" y_max_layer="1" y_max_fraction="1.00" />

- ``y_min_layer``, ``y_min_fraction`` specify layer ID and relative position in the layer corresponding to the lower limit :math:`r^\downarrow`
- ``y_max_layer``, ``y_max_fraction`` specify layer ID and relative position in the layer corresponding to the upper limit :math:`r^\uparrow`
- ``segment_type`` attribute is not used at the moment


region_occupy
^^^^^^^^^^^^^

This rule is similar to ``region_target`` but instead of checking if one interval is *within* the other, we are striving for *exact* match.

.. math::

    I = \max{\left(\frac{\min\left(a^\uparrow, r^\uparrow\right) - \max\left(a^\downarrow, r^\downarrow\right)}{\max\left(a^\uparrow - a^\downarrow, r^\uparrow - r^\downarrow\right)}, 0\right)}

I.e., we achieve optimal score :math:`1.0` if and only if two intervals coincide.

In placement rules file these rules are encoded with ``<rule type=region_occupy>`` elements:

.. code-block:: xml

    <rule id="dendrite, Layer_1"  type="region_occupy" segment_type="dendrite" y_min_layer="1" y_min_fraction="0.00" y_max_layer="1" y_max_fraction="1.00" />

Rule attributes are analogous to those used with ``region_target`` rule.

Combining the scores
~~~~~~~~~~~~~~~~~~~~

We aggregate strict scores :math:`L_k` with :math:`\min` function:

.. math::

    \hat{L} = {\min\limits_{k} L_k}

If there are no strict scores, :math:`\hat{L} = 1`.

By contrast, we aggregate optional scores :math:`I_j` in a slightly more "relaxed" way, with a harmonic mean.
That allows us to penalize low score for a particular rule heavier than a simple mean, but still "give it a chance" if other interval scores are high:

.. math::

    \hat{I} = \left(\frac{\sum\limits_{j} I_j^{-1}}{n}\right)^{-1}

Please note that if some optional score is close to zero (<0.001); the aggregated optional score would be zero, same as with strict scores.

If there are no optional scores or if optional scores are ignored, :math:`\hat{I} = 1`.

The final score :math:`\hat{S}` is a product of aggregated strict and optional scores:

.. math::

    \hat{S} = \hat{I} \cdot \hat{L}


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


Rotation file format
~~~~~~~~~~~~~~~~~~~~

The file that can be used with the ``--rotations`` parameter must by a YAML file
like in the following example:

.. code-block:: yaml

    rotations:
      - query: "mtype=='L23_MC'"
        distr: ["uniform", {"low": -3.14159, "high": 3.14159}]
        axis: y
      - query: "mtype=='L5_TPC:A' & etype=='bAC'"
        distr: ["norm", {"mean": 0.0, "sd": 1.0}]
        axis: y
      - query: {"mtype": "L5_TPC:B"}
        distr: ["vonmises", {"mu": 1.04720, "kappa": 2}]
        axis: y
      - query: "mtype=='L5_TPC:C'"
        distr: null
    default_rotation:
      distr: ["truncnorm", {"mean": 0.0, "sd": 1.0, "low": -3.14159, "high": 3.14159}]
      axis: y

Notes:

- The rotation defined in each rule is applied only to the cells matching the given ``query``.
- The rotations are applied in the same order as defined by the rules.
- If multiple rules affect the same cells, the rules defined later prevail over the former.
- The rotation rules are processed and logged in reverse order.
- A default rotation can be defined, and it's applied to all the cells not affected by the other rules.
- Axis can be one of ``x, y, z``. The same cells cannot be rotated multiple times around different
  axis (for example, rotate around ``y`` then rotate around ``z``).
- Angles are defined according to the right-hand rule: they have positive values when they represent
  a rotation that appears clockwise when looking in the positive direction of the axis,
  and negative values when the rotation appears counter-clockwise.
- The value of ``query`` can be:

  - a string, that's passed unchanged to the cells DataFrame using its query method
  - a dictionary, that's used to select the cells that match all the conditions.

- The value of ``distr`` is a list of two elements:

  - the first element is the name of the distribution
  - the second element is a dictionary containing the parameters of the distribution,
    where **any angle should be specified in radians**.

- See `Defining distributions in config files <https://bbpteam.epfl.ch/project/spaces/display/BBPNSE/Defining+distributions+in+config+files>`_
  for more details about the format of the distributions.
- See `Statistical functions <https://docs.scipy.org/doc/scipy/reference/stats.html>`_ in SciPy
  for the list of supported distributions, but note the following functions are wrapped
  and the parameters can be specified according to the following definitions:

  - ``norm(mean, sd)``
  - ``truncnorm(mean, sd, low, high)``
  - ``uniform(low, high)``
  - ``vonmises(mu, kappa)``

- If the value of ``distr`` is ``null``, then no rotation is applied to the selection of cells.
  This can be used for example when a default rotation is defined, and only a few morphologies
  shouldn't be rotated. When ``distr`` is ``null``, ``axis`` should be omitted.


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



Input Data
==========

.. _ref-data-atlas:

Atlas
-----

`choose-morphologies` relies on a set of volumetric datasets being provided by the atlas.

[PH]y
~~~~~

Position along brain region principal axis (for cortical regions that is the direction towards pia).

[PH]<layer>
~~~~~~~~~~~

For each `layer` used in the placement rules (see below), the corresponding volumetric dataset stores two numbers per voxel: lower and upper layer boundary along brain region principal axis.
Effectively, this allows to bind atlas-agnostic placement rules to a particular atlas space.

For instance, if we use `L1` to `L6` layer names in the placement rules, the atlas should have the following datasets ``[PH]y``, ``[PH]L1``, ``[PH]L2``, ``[PH]L3``, ``[PH]L4``, ``[PH]L5``, ``[PH]L6``.

``[PH]`` prefix stands for "placement hints" which is a historical way to address the approach used in |name|.


.. _ref-data-rules:

Placement rules
---------------

XML file defining a set of rules.

Root element ``<placement_rules>`` (no attributes) contains a collection of ``<rule>`` elements encoding rules described above.
Each ``<rule>`` has required ``id``, ``type`` attributes, plus additional attributes depending on the rule type (please refer to the rules description above for the details).
Rules are grouped into *rule sets*: `global`, which are applied to all the morphologies; and `mtype`-specific, applied solely to morphologies of the corresponding mtype.

This XML file might also specify additional random rotation applied to all the cells or specific mtypes.

Global rules
~~~~~~~~~~~~

Defined in ``<global_rule_set>`` element (no attributes), which can appear only once in XML file.

Usually global rules are hard limit rules.

Rule IDs should be unique.

Mtype rules
~~~~~~~~~~~

Defined in ``<mtype_rule_set>`` elements, which can appear multiple times in XML file.
Each element should have ``mtype`` attribute with the associated mtype (or `|`-separated list of mtypes).
No mtype can appear in more than one ``<mtype_rule_set>``.

Usually mtype rules are interval overlap rules.

Rule IDs should be unique within mtype rule set, and should not overlap with global rule IDs.

Example
~~~~~~~

.. code-block:: xml

    <placement_rules>

      <global_rule_set>
        <rule id="L1_hard_limit" type="below" segment_type="dendrite" y_layer="1" y_fraction="1.0"/>
        <rule id="L1_axon_hard_limit" type="below" segment_type="axon" y_layer="1" y_fraction="1.0"/>
      </global_rule_set>

      <mtype_rule_set mtype="L5_TPC:A|L5_TPC:B">
        <rule id="dendrite, Layer_1"  type="region_target" segment_type="dendrite" y_min_layer="1" y_min_fraction="0.00" y_max_layer="1" y_max_fraction="1.00" />
        <rule id="axon, Layer_1" type="region_target" segment_type="axon" y_min_layer="1" y_min_fraction="0.00" y_max_layer="1" y_max_fraction="1.00" />
      </mtype_rule_set>

    </placement_rules>

.. _ref-data-annotations:

Annotations
-----------

XML file which maps certain regions of the morphology (for instance, apical tuft) to corresponding placement rules.

Root element ``<annotations>`` (with single ``morphology`` attribute) contains a collection of ``<placement>`` elements.

Each ``<placement>`` element contains as attributes:

  * ``rule``: one of rule IDs defined by placement rules XML
  * ``y_min``, ``y_max``: :math:`Y`-range of morphology region, assuming morphology center is at :math:`y=0`

Example
~~~~~~~

.. code-block:: xml

    <annotations morphology="C030796A-P3">
      <placement rule="L1_hard_limit" y_max="1268.106" y_min="-323.641" />
      <placement rule="L1_axon_hard_limit" y_max="1186.089" y_min="-657.869" />
      <placement rule="dendrite, Layer_1" y_max="1270.0" y_min="1150.0" />
      <placement rule="axon, Layer_1" y_max="1230.0" y_min="1100.0" />
    </annotations>

For efficiency purpose, when collection of annotation files is used for ``choose-morphologies``, it is packed into a single JSON file with the following command delivered by |name| module:

.. code-block:: bash

    $ compact-annotations -o <OUTPUT> <ANNOTATION_DIR>

The result is a JSON file like:

::

  {
    "morph-1": {
      "L1_hard_limit": {
        "y_max": "96.4037744144",
        "y_min": "-224.580195025"
      },
    },
    "morph-2": {
      "L1_hard_limit": {
        "y_max": "350.432",
        "y_min": "-183.648"
      },
      "L4_UPC, dendrite, Layer_2 - Layer_1": {
        "y_max": "350.292",
        "y_min": "228.707"
      },
    },
    ...
  }

To choose only a subset of morphologies from a given annotation folder, one can provide an optional ``--morphdb`` argument with path to MorphDB file:

.. code-block:: bash

    $ compact-annotations --morphdb <MORPHDB> -o <OUTPUT> <ANNOTATION_DIR>

Acknowledgments
===============

|name| is a generalization of the approach originally proposed by `Michael Reimann <mailto:michael.reimann@epfl.ch>`_ and `Eilif Muller <mailto:eilif.mueller@epfl.ch>`_ for hexagonal mosaic circuits.


Reporting issues
================

|name| is maintained by BlueBrain NSE team at the moment.

Should you face any issue with using it, please submit a ticket to our `issue tracker <https://bbpteam.epfl.ch/project/issues/browse/NSETM>`_; or drop us an `email <mailto: bbp-ou-nse@groupes.epfl.ch>`_.
