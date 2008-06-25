function Neuron = getNeuronInfo(hdf5File)

[points, Neuron.beginnings, Neuron.endings, Neuron.typeInfo, Neuron.orderInfo, Neuron.branchcon] = mhdf5(hdf5File);

Neuron.X=points(:,1);
Neuron.Y=points(:,2);
Neuron.Z=points(:,3);
Neuron.Coordinates = [Neuron.X Neuron.Y Neuron.Z];
Neuron.Diameter = points(:,4);

Neuron.segmentsNB = length(Neuron.beginnings);
Neuron.neuronPointsNB = size(points,1);

[Neuron.branchOrder,Neuron.branchConnectivity,Neuron.pointsConnectivity] = getConnectivityANDOrder(Neuron.orderInfo,Neuron.segmentsNB,Neuron.endings);
