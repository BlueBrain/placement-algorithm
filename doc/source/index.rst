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

For each cell position in MVD3 we obtain its `distance` from the "bottom" layer, as well as total `height` along cell :math:`Y`-axis.

To reduce computation, we coarsen `distance` and `height`, specifying their `resolution`.
Note there is trade-off between performance and precision; 10 um resolution works fine in practice.

The coarsened positions are then grouped by (`region`, `mtype`, `etype`, `distance`, `height`), and joined to the morphology database using (`region`, `mtype`, `etype`) as the join key.

Each (`morphology`, `position`) pair from the resulting `candidate pool` is then given a score using the algorithm described in the detail in the next section.

Once each (`morphology`, `position`) pair is scored, we group them *by position*. Using scores as probability weights, we pick a morphology for every cell from the corresponding position group (sampling with replacement). If no morphology gets a positive score at the given position, all the corresponding cell positions are dropped.

The choice of morphologies can be tuned with :math:`\alpha` parameter, which specifies the exponential factor for each score. I.e., instead of using score :math:`S` as probability weights, one can use :math:`S^\alpha`. Using :math:`\alpha > 1` thus gives more preference to high scorers.


Calculating a placement score
-----------------------------

For each location we assign the morphology a score that reflects to what degree the applicable placement rules are fulfilled, if the morphology was placed at that location. This score is a real number from :math:`[0.0, 1.0]`, with :math:`0.0` indicating that a placement is impossible and :math:`1.0` indicating that all restrictions are fully met.

The set of rules applicable for each type is defined in :ref:`placement rules <ref-files-rules>` file.

Each morphology is :ref:`annotated <ref-files-annotations>` accordingly to pre-calculate Y-intervals for each region of interest (apical tuft, for instance).

Scores are first calculated for each separate rule and then combined to a total score.
If annotation corresponding to the rule is missing in morphology annotations, this rule is ignored when calculating the scores.

We distinguish two types of rules: *strict* ones and *optional* ones.
We aggregate scores for those differently, penalizing low *strict* score heavier than low *optional* score (see below).

In the following descriptions we will denote :math:`Y`-interval for a given morphology :math:`M` at a given position :math:`p` according to morphogy annotation with :math:`(a^\uparrow, a^\downarrow)`; and :math:`Y`-interval prescribed by a placement rule with :math:`(r^\uparrow, r^\downarrow)`.

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

Assuming :math:`(a^\uparrow, a^\downarrow)` is :math:`Y`-interval for a given morphology :math:`M` at a given position :math:`p` according to morphogy annotation; and :math:`(r^\uparrow, r^\downarrow)` is :math:`Y`-interval prescribed by a placement rule, we calculate the overlap between the two:

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

If there are no optional scores, :math:`\hat{I} = 1`.

The final score :math:`\hat{S}` is a product of aggregated strict and optional scores:

.. math::

    \hat{S} = \hat{I} \cdot \hat{L}


Usage
=====

|name| is distributed via `BBP Nix packages <https://bbpteam.epfl.ch/project/spaces/display/BBPHPC/Nix+Package+Manager>`_, and is available at BBP systems as ``nix/nse/placement-algorithm`` module.

.. code-block::console

    $ module load nix/nse/placement-algorithm

To ensure the result is reproducible, please consider using some specific `BBP archive S/W release <https://bbpteam.epfl.ch/project/spaces/display/BBPHPC/BBP+ARCHIVE+SOFTWARE+MODULES>`_.

The main executable provided in the module is ``assign-morphologies``, which is a all-in-one command to:

 - read `MVD3 <https://bbpteam.epfl.ch/documentation/Circuit%20Documentation-0.0.1/mvd3.html>`_ file with cell positions
 - fetch auxiliary volumetric datasets for an associated atlas
 - score each position-morphology combination
 - pick morphologies for every position based on score
 - output the result as a new MVD3


Parameters
----------

    --mvd3         Path to input MVD3 file [required]
    --morphdb      Path to MorphDB file [required]
    --atlas        Atlas URL [required]
    --atlas-cache  Atlas cache folder [optional, default: None]
    --resolution   Y-resolution (um) [optional, default: 10um]
    --annotations  Path to annotations folder [required]
    --rules        Path to placement rules file [required]
    --layers       Layer names ('bottom' to 'top', comma-separated) [required]
    --layer-ratio  Layer thickness ratio (comma-separated) [required]
    --alpha        [optional, default: 1.0]
    --seed         Random number generator seed [optional, default: 0]
    --ntasks       Number of Spark tasks to use for scoring [optional, default: 100]
    --debug        Dump additional output for debugging [optional]
    --output       Path to output MVD3 file [required]

For instance,

.. code-block:: bash

    $ assign-morphologies \
        --mvd3 circuit.mvd3.metypes \
        --atlas http://voxels.nexus.apps.bbp.epfl.ch/api/analytics/atlas/releases/7AD3A391-7E14-4250-89AD-51A4F16E0A46/ \
        --atlas-cache .atlas \
        --resolution 5 \
        --morphdb /gpfs/bbp.cscs.ch/project/proj42/entities/bionames/20180410/extNeuronDB.dat \
        --annotations /gpfs/bbp.cscs.ch/project/proj42/entities/morphologies/20180215/annotations \
        --rules /gpfs/bbp.cscs.ch/project/proj42/entities/bionames/20180410/placement_rules.xml \
        --layers SO,SP,SR,SLM \
        --layer-ratio 170,60,280,150 \
        --alpha 3.0 \
        --seed 0

Under the hood ``assign-morphologies`` is a wrapper Bash script which launches ``spark-submit`` with a specific Python script.
It's up to the user to ensure that ``spark-submit`` command is available in the environment, and is configured properly.

Files
=====

.. _ref-files-rules:

Placement rules
---------------

XML file defining a set of rules.

Root element ``<placement_rules>`` (no attributes) contains a collection of ``<rule>`` elements encoding rules described above.
Each ``<rule>`` has required ``id``, ``type`` attributes, plus additional attributes depending on the rule type (please refer to the rules description above for the details).
Rules are grouped into *rule sets*: `global`, which are applied to all the morphologies; and `mtype`-specific, applied solely to morphologies of the corresponding mtype.

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

.. _ref-files-annotations:

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


Acknowledgments
===============

|name| is a generalization of the approach originally proposed by `Michael Reimann <mailto:michael.reimann@epfl.ch>`_ and `Eilif Muller <mailto:eilif.mueller@epfl.ch>`_ for hexagonal mosaic circuits.


Reporting issues
================

|name| is maintained by BlueBrain NSE team at the moment.

Should you face any issue with using it, please submit a ticket to our `issue tracker <https://bbpteam.epfl.ch/project/issues/browse/NSETM>`_; or drop us an `email <mailto: bbp-ou-nse@groupes.epfl.ch>`_.
