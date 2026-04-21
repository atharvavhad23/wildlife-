const mongoose = require("mongoose");

const predictionHistorySchema = new mongoose.Schema(
  {
    predictionResultId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "PredictionResult",
      required: true,
      index: true,
    },
    inputId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "PredictionInput",
      required: true,
      index: true,
    },
    locationName: {
      type: String,
      trim: true,
      maxlength: 140,
      index: true,
    },
    baselineDensityPerSqKm: {
      type: Number,
      min: 0,
    },
    currentDensityPerSqKm: {
      type: Number,
      required: true,
      min: 0,
      index: true,
    },
    changePercent: {
      type: Number,
      index: true,
    },
    trend: {
      type: String,
      enum: ["increase", "decrease", "stable"],
      index: true,
    },
    sequenceNo: {
      type: Number,
      required: true,
      min: 1,
    },
  },
  {
    timestamps: true,
    collection: "prediction_history",
  }
);

predictionHistorySchema.index({ inputId: 1, sequenceNo: 1 }, { unique: true });
predictionHistorySchema.index({ locationName: 1, createdAt: -1 });
predictionHistorySchema.index({ trend: 1, createdAt: -1 });

module.exports = mongoose.model("PredictionHistory", predictionHistorySchema);
