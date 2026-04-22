import type { RenderTileResult } from "@developmentseed/deck.gl-raster";
import {
  Colormap,
  LinearRescale,
} from "@developmentseed/deck.gl-raster/gpu-modules";
import type { Texture } from "@luma.gl/core";
import type { ColormapOption } from "../gpu/colormap.js";
import { SampleTexture2DArray } from "../gpu/sample-texture-2d-array.js";
import type { AnomalyTileData } from "./get-tile-data.js";

export type MakeRenderTileArgs = {
  dateIdx: number;
  colormapTexture: Texture;
  colormap: ColormapOption;
  rescaleMin: number;
  rescaleMax: number;
};

export function makeRenderTile(args: MakeRenderTileArgs) {
  const { dateIdx, colormapTexture, colormap, rescaleMin, rescaleMax } = args;
  return function renderTile(data: AnomalyTileData): RenderTileResult {
    return {
      renderPipeline: [
        {
          module: SampleTexture2DArray,
          props: { dataTex: data.texture, layerIndex: dateIdx },
        },
        {
          module: LinearRescale,
          props: { rescaleMin, rescaleMax },
        },
        {
          module: Colormap,
          props: { colormapTexture, colormapIndex: colormap.index, reversed: colormap.reversed },
        },
      ],
    };
  };
}
