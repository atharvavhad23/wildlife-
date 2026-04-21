const mongoose = require("mongoose");

const occurrenceSchema = new mongoose.Schema(
  {
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
    observationId: {
      type: String,
      trim: true,
      index: true,
    },
    source: {
      type: String,
      trim: true,
      enum: ["csv", "inaturalist", "manual"],
      default: "csv",
      index: true,
    },
    observedAt: {
      type: Date,
      required: true,
      index: true,
    },
    locationName: {
      type: String,
      trim: true,
      maxlength: 180,
      index: true,
    },
    coordinates: {
      type: {
        type: String,
        enum: ["Point"],
        default: "Point",
      },
      coordinates: {
        type: [Number],
        validate: {
          validator: (arr) => arr.length === 2,
          message: "Coordinates must include [longitude, latitude]",
        },
      },
    },
    observerName: {
      type: String,
      trim: true,
      maxlength: 120,
    },
    quantityObserved: {
      type: Number,
      min: 0,
      default: 1,
    },
    photoCount: {
      type: Number,
      min: 0,
      default: 0,
      index: true,
    },
    metadata: {
      type: mongoose.Schema.Types.Mixed,
      default: null,
    },
  },
  {
    timestamps: true,
    collection: "occurrence",
  }
);

occurrenceSchema.index({ coordinates: "2dsphere" });
occurrenceSchema.index({ categoryId: 1, observedAt: -1 });
occurrenceSchema.index({ speciesId: 1, observedAt: -1 });
occurrenceSchema.index({ source: 1, observationId: 1 });

module.exports = mongoose.model("Occurrence", occurrenceSchema);
