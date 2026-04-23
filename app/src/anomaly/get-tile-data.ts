import type {
  GetTileDataOptions,
  MinimalZarrTileData,
} from "@developmentseed/deck.gl-zarr";
import type { Readable } from "@zarrita/storage";
import type { Texture } from "@luma.gl/core";
import * as zarr from "zarrita";

/**
 * Per-tile data: a Texture2DArray stacking all valid_date frames
 * for one spatial chunk.
 */
export type AnomalyTileData = MinimalZarrTileData & {
  /** r32float Texture2DArray, depth = number of valid_date entries. */
  texture: Texture;
  /** Number of frames packed in this tile texture. */
  depth: number;
};

/**
 * Slice one spatial chunk of an anomaly variable and upload it as a
 * Texture2DArray (one layer per valid_date).
 */
export async function getTileData(
  arr: zarr.Array<zarr.DataType, Readable>,
  options: GetTileDataOptions,
): Promise<AnomalyTileData> {
  const { device, sliceSpec, width, height, signal } = options;

  const result = await zarr.get(
    arr as zarr.Array<"float32", Readable>,
    sliceSpec as Parameters<typeof zarr.get>[1],
    { opts: { signal } },
  );

  if (result.shape.length !== 3) {
    throw new Error(
      `Expected 3D sliced result (valid_date, y, x), got shape [${result.shape.join(", ")}]`,
    );
  }
  const depth = result.shape[0];
  if (result.shape[1] !== height || result.shape[2] !== width) {
    throw new Error(
      `Tile shape mismatch: expected [*, ${height}, ${width}], got [${result.shape.join(", ")}]`,
    );
  }

  const data = result.data as Float32Array;

  const texture = device.createTexture({
    dimension: "2d-array",
    format: "r32float",
    width,
    height,
    depth,
    mipLevels: 1,
    data,
    sampler: {
      minFilter: "nearest",
      magFilter: "nearest",
      addressModeU: "clamp-to-edge",
      addressModeV: "clamp-to-edge",
    },
  });

  return { texture, depth, width, height, byteLength: data.byteLength };
}
