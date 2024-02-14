import express from 'express';

import { createNewComputeProvider, deleteComputeProvider, getAllComputeProviders, updateComputeProvider } from '../controllers/computeproviders'

export default (router: express.Router) => {
    router.post('/computeprovider', createNewComputeProvider);
    router.get('/computeprovider', getAllComputeProviders);
    router.delete('/computeprovider/:id', deleteComputeProvider);
    router.patch('/computeprovider/:id', updateComputeProvider);
}
