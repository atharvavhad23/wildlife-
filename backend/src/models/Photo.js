const mongoose = require("mongoose");

const photoSchema = new mongoose.Schema(
  {
    occurrenceId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Occurrence",
      required: true,
      index: true,
    },
    speciesId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Species",
      required: true,
      index: true,
    },
    categoryId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Category",
      required: true,
      index: true,
    },
    source: {
      type: String,
      trim: true,
      enum: ["inaturalist", "csv", "manual"],
      default: "inaturalist",
      index: true,
    },
    imageUrl: {
      type: String,
      required: true,
      trim: true,
      maxlength: 1000,
    },
    thumbnailUrl: {
      type: String,
      trim: true,
      maxlength: 1000,
    },
    proxyUrl: {
      type: String,
      trim: true,
      maxlength: 1000,
    },
    attribution: {
      type: String,
      trim: true,
      maxlength: 240,
    },
    isPrimary: {
      type: Boolean,
      default: false,
      index: true,
    },
    status: {
      type: String,
      enum: ["active", "failed", "archived"],
      default: "active",
      index: true,
    },
    failedAt: {
      type: Date,
      default: null,
    },
  },
  {
    timestamps: true,
    collection: "photo",
  }
);

photoSchema.index({ categoryId: 1, createdAt: -1 });
photoSchema.index({ speciesId: 1, createdAt: -1 });
photoSchema.index({ occurrenceId: 1, isPrimary: -1, createdAt: -1 });
photoSchema.index({ status: 1, createdAt: -1 });

module.exports = mongoose.model("Photo", photoSchema);
