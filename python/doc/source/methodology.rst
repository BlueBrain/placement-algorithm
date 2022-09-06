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
