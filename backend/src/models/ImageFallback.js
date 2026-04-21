const mongoose = require("mongoose");

const imageFallbackSchema = new mongoose.Schema(
  {
    photoId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Photo",
      required: true,
      index: true,
    },
    originalUrl: {
      type: String,
      required: true,
      trim: true,
      maxlength: 1000,
    },
    fallbackUrl: {
      type: String,
      required: true,
      trim: true,
      maxlength: 1000,
    },
    proxyUrl: {
      type: String,
      trim: true,
      maxlength: 1000,
    },
    failureCode: {
      type: String,
      trim: true,
      maxlength: 100,
      index: true,
    },
    failureReason: {
      type: String,
      trim: true,
      maxlength: 400,
    },
    attemptCount: {
      type: Number,
      min: 1,
      default: 1,
    },
    recovered: {
      type: Boolean,
      default: false,
      index: true,
    },
  },
  {
    timestamps: true,
    collection: "image_fallback",
  }
);

imageFallbackSchema.index({ photoId: 1, createdAt: -1 });
imageFallbackSchema.index({ recovered: 1, createdAt: -1 });

module.exports = mongoose.model("ImageFallback", imageFallbackSchema);
