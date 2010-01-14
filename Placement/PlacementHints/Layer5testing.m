function Layer5testing(filePath, path)
% Reads the morpho parameters file and extracts the parameters from it and
% then assigns an index to the neuron in the neuronDB.dat file. The index
% varies between 0 and 1 when an index can be assigned otherwise it is left
% to -1

% the placement is done based on the dendrite height

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%  PARAMETERS OF THE ALGORITHM %%%%%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%Types of neurons to be considered for a placement hint
neuronTypes = getTypes(path);
%Number of these types
TypesNB = length(neuronTypes);
%Layer Definition
Layer = getLayerDefinition();
%Max number of bins per layer
binsNB = 10;
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%******************LOAD THE FILES NEEDED

%load the morphology parameters file
fid = fopen(filePath);
A =textscan(fid,'%s%f%f%f%f%f%f%f%f');

%get info needed from morphology file (input file)
neuronName = A{1,1};
%%% the name contains the .h5 extension so we need to remove it:
neuronName = strrep(neuronName,'.h5','');
maxHeightAxon = A{1,2};
maxDepthAxon =  A{1,3};
maxHeightDendrite = A{1,4};
maxDepthDendrite =  A{1,5};
maxRadiusAxon = A{1,6};
maxRadiusDendrite =A{1,7};
fclose(fid);

%get info needed from neuronDB file (output file)
%load the NeuronDB.dat file
fid = fopen(path);

%***********************************
%***********************************
%%%%%% REMOVE THE %f ***************
%***********************************
%***********************************

A = textscan(fid,'%s%d%s%f');

neuron = A{1,1};
layerNB = A{1,2};
type = A{1,3};

fclose(fid);

dendriteHeights = [];
axonHeights = [];

neuronsNB = length(neuron);
for i = 1:neuronsNB
    if strcmp(type{i},'L5CSPC')
    index=strmatch(neuron{i},neuronName);
    dendriteHeights = [dendriteHeights maxHeightDendrite(index)];
    axonHeights = [axonHeights maxHeightAxon(index)];
    end
    
end

figure
subplot(2,2,1)
hold on
hist(dendriteHeights)
plot([Layer(1).To-Layer(5).From Layer(1).To-Layer(5).From],[0 10],'r-','LineWidth',1)
xlabel('Dendrite Height (?m)')
ylabel('# of neurons')
titleText = sprintf('L5CSPCs Dendrite Height (n= %d)',length(dendriteHeights));
title(titleText);
hold off;

subplot(2,2,2)
hold on
plot(1:length(dendriteHeights),dendriteHeights,'k*');
plot([0,35], [Layer(1).To-Layer(5).From Layer(1).To-Layer(5).From],'r-','LineWidth',1)

xlabel('Neurons')
ylabel('Dendrite Height (?m)')
titleText = sprintf('L5CSPCs Dendrite Height (n= %d)',length(dendriteHeights));
title(titleText);
axis([0 35 0 1500])
hold off

subplot(2,2,3)
hold on
hist(axonHeights)
plot([Layer(1).To-Layer(5).From Layer(1).To-Layer(5).From],[0 10],'r-','LineWidth',1)
xlabel('Axon Height (?m)')
ylabel('# of neurons')
titleText = sprintf('L5CSPCs Dendrite Height (n= %d)',length(axonHeights));
title(titleText);
hold off;

subplot(2,2,4)
hold on
plot(1:length(axonHeights),axonHeights,'k*');
plot([0,35], [Layer(1).To-Layer(5).From Layer(1).To-Layer(5).From],'r-','LineWidth',1)
xlabel('Neurons')
ylabel('Axon Height(?m)')
titleText = sprintf('L5CSPCs Axon Height (n= %d)',length(axonHeights));
title(titleText);
axis([0 35 0 1500])
hold off

