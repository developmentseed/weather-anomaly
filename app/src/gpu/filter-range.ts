import type { ShaderModule } from "@luma.gl/shadertools";

export type FilterRangeProps = {
  /** Minimum value (inclusive). Pixels strictly below are discarded. */
  filterMin: number;
  /** Maximum value (inclusive). Pixels strictly above are discarded. */
  filterMax: number;
};

const MODULE_NAME = "filterRange";

/**
 * Discards fragments whose scalar value (`color.r`) falls outside
 * `[filterMin, filterMax]`. Runs after SampleTexture2DArray (which writes
 * the raw data value into color.r) and before LinearRescale.
 */
export const FilterRange = {
  name: MODULE_NAME,
  fs: `\
uniform ${MODULE_NAME}Uniforms {
  float filterMin;
  float filterMax;
} ${MODULE_NAME};
`,
  inject: {
    "fs:DECKGL_FILTER_COLOR": /* glsl */ `
      if (color.r < ${MODULE_NAME}.filterMin || color.r > ${MODULE_NAME}.filterMax) {
        discard;
      }
    `,
  },
  uniformTypes: {
    filterMin: "f32",
    filterMax: "f32",
  },
  getUniforms: (props: Partial<FilterRangeProps>) => {
    return {
      filterMin: props.filterMin ?? Number.NEGATIVE_INFINITY,
      filterMax: props.filterMax ?? Number.POSITIVE_INFINITY,
    };
  },
} as const satisfies ShaderModule<FilterRangeProps>;
