Status doc

PCP testbed er lovende.
ønskede forbedringer:

Gradvis forfining af opløsning under bearbdejning (dvs. voxel size stiger løbende, optimiserings opgave)

Oprydning i koden. - Løbende as of now

Stærkere værktøj til Initial alignement (Kan vi finde omdrejnignsakse, og komme med bedre bud?)
Lige nu anvendes en kendt vinkel, og en translation baseret på densitet. Lidt primitivt.
- Ovenstående er løst ved zero-transform 

Bedre skalering af Max dist., outlier/noise removal etc, således det afhænger af voxel size., Done

Bedre forklaring af normal space sampling - er nu lavet i overleaf! 

Add auto cropping - Done, function added, needs refinement

Tilføj Normal correspondeces til ICP. Burde gøre metoden mere robust. - Done, added as new func.

Bedre indsigt i ICP. Lige nu er der f.eks. ingen data på hvor mange iterationer etc det tog...  - Done, new func has logging

Fix Testbed/update to zero transform scheme - Done!
Function til Ola, alignment af STL - Done!

Combined transformation som json - Toke*

Ny func til 2 pcd, ikke fil dest.

KD tree mean value

Test decompose transformation, incorporate into scan-func - POSTPONED - for now, use the norm of the ICP transform

MDP AKTIV:

Bedre outlier removal. Der er noget støj tilbage på meshen. - Toke foreslår DBSCAN

Skalering - Pending - Ola kigger på det?

Test Poisson vs almen Voxel

Ideas for outlier removal:
Thickness requirement (Kill zero-thickness points)
(Ask gpt)

Docker

Test rotations
