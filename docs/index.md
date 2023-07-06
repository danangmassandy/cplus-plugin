# CPLUS QGIS plugin

## Introduction

The challenge of mitigating climate change and achieving global and national climate targets requires innovative and
holistic approaches. In this pursuit, the Climate Positive Land Use Strategy (CPLUS) decision support tool has emerged
as a crucial resource. CPLUS is a spatially-explicit roadmap designed to guide land-use planning strategies, utilizing
natural climate solutions to drive meaningful and sustainable change. The CPLUS decision support tool combines
open-source technology, localized data sets, and modelled products to empower policymakers, land managers,
and stakeholders in making informed decisions. By integrating spatial information, such as land cover, carbon stocks,
and potential for carbon sequestration, CPLUS enables the identification of key areas for intervention and investment.
By prioritizing these nature-based interventions, CPLUS seeks to harness the power of ecosystems and optimize their
climate mitigation potential.

One of the distinguishing features of CPLUS is its ability to address both global and national climate targets.
While global climate targets provide a broad framework for action, national targets require context-specific strategies
tailored to the unique characteristics of each country. The CPLUS decision support tool considers these diverse factors
and assists in designing land-use planning strategies that align with national commitments while contributing to global
climate goals. Furthermore, CPLUS recognizes that effective land-use planning involves collaboration and engagement
among various stakeholders. It fosters dialogue and cooperation between governments, local communities, indigenous
groups, conservation organizations, and private entities, facilitating the development of inclusive and equitable
solutions. By involving diverse perspectives and expertise, CPLUS ensures that the decision-making process is
participatory and informed by local knowledge.

Piloted in the Bushbuckridge Municipality in the Kruger to Canyons Biosphere of South Africa, the CPLUS framework was
tested with a diverse set of stakeholders to identify land use priorities and understand the carbon benefits and
biodiversity, ecosystem services co-benefits of different scenarios.

## CPLUS model

### Implementation models

**Figure 1** shows a flow diagram of the CPLUS analysis model.

![Simplified analysis model](img/cplus_core/simplified_analysis_model.svg)

*Figure 1: Simplified analysis model*

### Algorithms

Shown in **Figure 2** is the algorithms applied by the CPLUS model analysis model.

![Simplified analysis model with algorithms](img/cplus_core/workflow_with_algorithms.svg)

*Figure 2: CPLUS simplified analysis workflow with algorithms*

### QGIS model

The model has been implemented in QGIS, which makes use of the Raster calculator tool to calculate
each of the model's algorithms. Once the algorithms finish, a Highest Position calculation is
done. This workflow is outlined in **Figure 3**.

![QGIS model](img/cplus_core/qgis_model.svg)

*Figure 3: Graphical model created in QGIS*

### References

- https://www.pnas.org/doi/10.1073/pnas.1710465114
- https://royalsocietypublishing.org/doi/10.1098/rstb.2019.0126