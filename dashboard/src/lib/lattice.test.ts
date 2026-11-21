// The tree drawn in the Real Options section must agree with the tested CRR engine.
import { describe, expect, it } from "vitest";
import { binomialCall, binomialLattice } from "./finance";

describe("binomial lattice used for the tree diagram", () => {
  it("root equals binomialCall (European and American, with and without leakage)", () => {
    for (const [am, q] of [[false, 0], [true, 0], [true, 0.03]] as const) {
      const L = binomialLattice(18009.8, 18009.8, 0.0253, 3, 0.137862, 4, am, q);
      expect(L.nodes[0][0].v).toBeCloseTo(binomialCall(18009.8, 18009.8, 0.0253, 3, 0.137862, 4, am, q), 6);
    }
  });
});
