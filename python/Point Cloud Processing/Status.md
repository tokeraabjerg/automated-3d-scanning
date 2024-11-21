Status doc

PCP testbed er lovende.
ønskede forbedringer:

Gradvis forfining af opløsning under bearbdejning (dvs. voxel size stiger løbende, optimiserings opgave)

Oprydning i koden.

Stærkere værktøj til Initial alignement (Kan vi finde omdrejnignsakse, og komme med bedre bud?)
Lige nu anvendes en kendt vinkel, og en translation baseret på densitet. Lidt primitivt.

Bedre skalering af Max dist., outlier/noise removal etc, således det afhænger af voxel size.

Bedre forklaring af normal space sampling - er nu lavet i overleaf! 

Bedre outlier removal. Der er noget støj tilbage på meshen. - Toke foreslår DBSCAN


MDP AKTIV:
Bedre indsigt i ICP. Lige nu er der f.eks. ingen data på hvor mange iterationer etc det tog...  

Tilføj Normal correspondeces til ICP. Burde gøre metoden mere robust.

