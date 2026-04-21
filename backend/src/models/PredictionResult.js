 const mongoose = require("mongoose");

const predictionResultSchema = new mongoose.Schema(
  {
    inputId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "PredictionInput",
      required: true,
      unique: true,
      index: true,
    },
    categoryId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Category",
      index: true,
    },
    speciesId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Species",
      index: true,
    },
    predictedDensityPerSqKm: {
      type: Number,
      required: true,
      min: 0,
      index: true,
    },
    confidenceScore: {
      type: Number,
      min: 0,
      max: 1,
    },
    modelVersion: {
      type: String,
      required: true,
      trim: true,
      maxlength: 100,
      index: true,
    },
    modelRuntimeMs: {
      type: Number,
      min: 0,
    },
    predictionLabel: {
      type: String,
      trim: true,
      maxlength: 100,
    },
    rawOutput: {
      type: mongoose.Schema.Types.Mixed,
      default: null,
    },
  },
  {
    timestamps: true,
    collection: "prediction_result",
  }
);

predictionResultSchema.index({ createdAt: -1 });
predictionResultSchema.index({ categoryId: 1, createdAt: -1 });
predictionResultSchema.index({ speciesId: 1, createdAt: -1 });

module.exports = mongoose.model("PredictionResult", predictionResultSchema);
