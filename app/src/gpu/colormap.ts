import {
  COLORMAP_INDEX,
  createColormapTexture,
  decodeColormapSprite,
} from "@developmentseed/deck.gl-raster/gpu-modules";
import colormapsUrl from "@developmentseed/deck.gl-raster/gpu-modules/colormaps.png?url";

export { createColormapTexture, COLORMAP_INDEX };

export const COLORMAPS = [
  { label: "RdBu (diverging)",   index: COLORMAP_INDEX.rdbu,    reversed: true  },
  { label: "Coolwarm (diverging)",index: COLORMAP_INDEX.coolwarm,reversed: false },
  { label: "Inferno (thermal)",   index: COLORMAP_INDEX.inferno, reversed: false },
] as const;

export type ColormapOption = (typeof COLORMAPS)[number];

export async function loadColormapSprite(): Promise<ImageData> {
  const bytes = await (await fetch(colormapsUrl)).arrayBuffer();
  return decodeColormapSprite(bytes);
}
