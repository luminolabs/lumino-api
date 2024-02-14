import mongoose from "mongoose";

const ComputeProviderSchema = new mongoose.Schema({
    username: { type: String, required: true },
    email: { type: String, required: true },
    name: { type: String, required: true },
    resources: { type: String, required: true },
    available: { type: Boolean, required: true },
    ipaddress: { type: String, required: true }
});

export const ComputeProviderModel = mongoose.model('ComputeProvider', ComputeProviderSchema);

export const getComputeProviders = () => ComputeProviderModel.find();

export const getComputeProviderByEmail = (email: string) => ComputeProviderModel.findOne( { email } );

export const getComputeProviderById = (id: string) => ComputeProviderModel.findById(id);
export const createComputeProvider = (values: Record<string, any>) => new ComputeProviderModel(values)
    .save().then((computeprovider) => computeprovider.toObject());

export const deleteComputeProviderById = (id: string) => ComputeProviderModel.findOneAndDelete({ _id: id });
export const updateComputeProviderById = (id: string, values: Record<string, any>) => ComputeProviderModel.findByIdAndUpdate(id, values);
