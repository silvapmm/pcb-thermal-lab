# User guide outline (import chapter, when the feature is built)

1. **The BOM file.** Step 1 lists a bill of materials with the role "BOM (bill of materials)". It is found by its columns (a designator column plus value, footprint, quantity or part number columns). Add it with the other files or with Add files. A BOM that is also a placement table (it has X and Y columns) is read as a placement file; change the role if the program guessed wrong.
2. **What the BOM does.** It proposes the Role of each part in step 2 and marks parts that are not populated. It never sets a power and never moves a part. The proposal comes from the names (designator letter, footprint, value): a guess, listed with its reason in the tooltip.
3. **Roles.** Component: a part with a junction (IC, transistor, diode, LED); Source: a part that only dissipates (resistor, inductor, ferrite, fuse). Connectors, switches, test points, holes and capacitors are not offered as heat sources unless ticked by hand.
4. **Not populated.** A part the BOM marks DNP or DNI is unticked and says "not populated (BOM)"; tick it to simulate it anyway.
5. **Re-import.** The BOM is read again; the roles you changed stay; the line of the re-import says which parts changed role in the BOM.
6. **Package.** With Export package and the box "Include the source files", the BOM is stored with the Gerbers (it carries part numbers and prices: leave the box off when you share a project).
7. Tooltips: the BOM line, the Role cell proposal, the "not populated" cell, "in BOM only", "not in BOM".
