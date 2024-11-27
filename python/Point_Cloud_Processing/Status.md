Status doc

PCP testbed er lovende.
ønskede forbedringer:

Gradvis forfining af opløsning under bearbdejning (dvs. voxel size stiger løbende, optimiserings opgave)

Oprydning i koden. - Løbende as of now

Stærkere værktøj til Initial alignement (Kan vi finde omdrejnignsakse, og komme med bedre bud?)
Lige nu anvendes en kendt vinkel, og en translation baseret på densitet. Lidt primitivt.
- Ovenstående er løst ved zero-transform 

Bedre skalering af Max dist., outlier/noise removal etc, således det afhænger af voxel size.

Bedre forklaring af normal space sampling - er nu lavet i overleaf! 



MDP AKTIV:
Bedre indsigt i ICP. Lige nu er der f.eks. ingen data på hvor mange iterationer etc det tog...  - Done, new func has logging

Tilføj Normal correspondeces til ICP. Burde gøre metoden mere robust. - Done, added as new func.

Fix Testbed/update to zero transform scheme - Pending

Add auto cropping - Current

Bedre outlier removal. Der er noget støj tilbage på meshen. - Toke foreslår DBSCAN

Skalering - Pending