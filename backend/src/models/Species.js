const mongoose = require("mongoose");

const speciesSchema = new mongoose.Schema(
  {
    categoryId: {
      type: mongoose.Schema.Types.ObjectId,
      ref: "Category",
      required: true,
      index: true,
    },
    commonName: {
      type: String,
      required: true,
      trim: true,
      maxlength: 120,
      index: true,
    },
    scientificName: {
      type: String,
      required: true,
      trim: true,
      maxlength: 160,
      index: true,
    },
    iucnStatus: {
      type: String,
      trim: true,
      maxlength: 40,
      index: true,
    },
    description: {
      type: String,
      trim: true,
      maxlength: 2000,
    },
    tags: {
      type: [String],
      default: [],
    },
    isActive: {
      type: Boolean,
      default: true,
      index: true,
    },
  },
  {
    timestamps: true,
    collection: "species",
  }
);

speciesSchema.index({ categoryId: 1, commonName: 1 });
speciesSchema.index({ categoryId: 1, scientificName: 1 }, { unique: true });
speciesSchema.index({ commonName: "text", scientificName: "text", description: "text" });

module.exports = mongoose.model("Species", speciesSchema);
