const mongoose = require("mongoose");

const cacheLogSchema = new mongoose.Schema(
  {
    cacheKey: {
      type: String,
      required: true,
      trim: true,
      maxlength: 300,
      index: true,
    },
    endpoint: {
      type: String,
      required: true,
      trim: true,
      maxlength: 200,
      index: true,
    },
    categoryKey: {
      type: String,
      trim: true,
      enum: ["animals", "birds", "insects"],
      index: true,
    },
    status: {
      type: String,
      required: true,
      enum: ["hit", "miss", "refresh", "expired"],
      index: true,
    },
    ttlSeconds: {
      type: Number,
      min: 1,
    },
    expiresAt: {
      type: Date,
      index: true,
    },
    responseTimeMs: {
      type: Number,
      min: 0,
    },
    payloadSizeBytes: {
      type: Number,
      min: 0,
    },
  },
  {
    timestamps: true,
    collection: "cache_log",
  }
);

cacheLogSchema.index({ cacheKey: 1, createdAt: -1 });
cacheLogSchema.index({ endpoint: 1, status: 1, createdAt: -1 });
cacheLogSchema.index({ expiresAt: 1 }, { expireAfterSeconds: 0 });

module.exports = mongoose.model("CacheLog", cacheLogSchema);
