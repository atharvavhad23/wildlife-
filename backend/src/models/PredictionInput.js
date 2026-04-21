const mongoose = require("mongoose");

const predictionInputSchema = new mongoose.Schema(
  {
    sessionId: {
      type: String,
      trim: true,
      index: true,
    },
    locationName: {
      type: String,
      trim: true,
      maxlength: 140,
      index: true,
    },
    coordinates: {
      type: {
        type: String,
        enum: ["Point"],
      },
      coordinates: {
        type: [Number],
        validate: {
          validator: (arr) => arr.length === 2,
          message: "Coordinates must include [longitude, latitude]",
        },
      },
    },
    vegetationIndex: {
      type: Number,
      required: true,
      min: 0,
      max: 1,
    },
    temperature: {
      type: Number,
      required: true,
      min: -50,
      max: 70,
    },
    rainfall: {
      type: Number,
      required: true,
      min: 0,
      max: 20000,
    },
    waterAvailability: {
      type: Number,
      required: true,
      min: 0,
      max: 1,
    },
    landUse: {
      type: Number,
      required: true,
      min: 0,
      max: 1,
    },
    humanDisturbance: {
      type: Number,
      required: true,
      min: 0,
      max: 1,
    },
    source: {
      type: String,
      trim: true,
      enum: ["api", "csv", "batch", "manual"],
      default: "api",
      index: true,
    },
  },
  {
    timestamps: true,
    collection: "prediction_input",
  }
);

predictionInputSchema.index({ coordinates: "2dsphere" });
predictionInputSchema.index({ createdAt: -1 });
predictionInputSchema.index({ locationName: 1, createdAt: -1 });

module.exports = mongoose.model("PredictionInput", predictionInputSchema);
