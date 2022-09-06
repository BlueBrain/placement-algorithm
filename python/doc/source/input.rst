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


Rotation file
-------------

YAML file that can be used with the ``--rotations`` parameter of ``assign-morphologies``.

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

Example
~~~~~~~

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
