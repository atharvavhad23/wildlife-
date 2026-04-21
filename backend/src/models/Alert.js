const mongoose = require("mongoose");

const alertSchema = new mongoose.Schema(
  {
    predictionHistoryId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "PredictionHistory",
      required: true,
      index: true,
    },
    severity: {
      type: String,
      required: true,
      enum: ["low", "medium", "high", "critical"],
      index: true,
    },
    alertType: {
      type: String,
      required: true,
      trim: true,
      enum: ["density_drop", "anomaly", "data_quality"],
      index: true,
    },
    thresholdValue: {
      type: Number,
      required: true,
    },
    observedValue: {
      type: Number,
      required: true,
    },
    message: {
      type: String,
      required: true,
      trim: true,
      maxlength: 400,
    },
    status: {
      type: String,
      enum: ["open", "acknowledged", "resolved"],
      default: "open",
      index: true,
    },
    resolvedAt: {
      type: Date,
      default: null,
    },
  },
  {
    timestamps: true,
    collection: "alerts",
  }
);

alertSchema.index({ status: 1, createdAt: -1 });
alertSchema.index({ severity: 1, createdAt: -1 });
alertSchema.index({ alertType: 1, createdAt: -1 });

module.exports = mongoose.model("Alert", alertSchema);
