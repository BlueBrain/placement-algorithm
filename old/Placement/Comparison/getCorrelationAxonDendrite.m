function getCorrelationAxonDendrite(filePath, path)
%pass as input the Morphology file and obtain a plot of the Dendrite Height
%versus the Axon Height, and a second plot with a different color for each
%layer cells

%Types of neurons to be considered for a placement hint
neuronTypes = { 'SSC','L2PC','L3PC','L4PC','L4SP','L4SS','L5CSPC','L5CHPC','L6CTPC','L6CCPC','L6CSPC' };

%Number of these types
TypesNB = length(neuronTypes);

%******************LOAD THE FILES NEEDED

%load the morphology parameters file
fid = fopen(filePath);
A =textscan(fid,'%s%f%f%f%f%f%f%f%f');

%get info needed from morphology file (input file)
neuronName = A{1,1};
neuronName = strrep(neuronName,'.h5','');

maxHeightAxon = A{1,2};
maxHeightDendrite = A{1,4};
fclose(fid)

%***********************************

%load the NeuronDB.dat file
fid = fopen(path);
A = textscan(fid,'%s%d%s');

neuron = A{1,1};
layerNB = A{1,2};
type = A{1,3};

fclose(fid)

%***********************************

%initializing
MPIndices=[];
maxHAarray=[];
maxHDarray=[];
MPIndicesTwo=[];


 fig = figure;
 hold on

for i=1:TypesNB
     cType = neuronTypes{i};
     cTypeIndices = strmatch(cType,type,'exact');

      if isempty(cTypeIndices)
       TEXT = sprintf(' ****************The are no cells defined as %s ****************',cType);
       disp(TEXT)
       continue        
      end

MPIndices(cTypeIndices)= getMorphIndices(cTypeIndices, neuron, neuronName);
MPIndicesTwo(cTypeIndices)= getMorphIndices(cTypeIndices, neuron, neuronName);
end

minus= find(MPIndices==0);
MPIndices(minus)=[];

maxHAarray=maxHeightAxon(MPIndices);
maxHDarray=maxHeightDendrite(MPIndices);

plot (maxHAarray, maxHDarray,'rx')  

xlabel('Axon Height')
ylabel('Dendrite Height')
title('Correlation between Dendrite and Axon Height');

%allows clicking on a point in a graph and displaying the name of the
%corresponding neuron
datacursormode on 
dcm_obj = datacursormode(fig);
set(dcm_obj,'UpdateFcn',{@myupdatefcn,MPIndices, neuronName, dcm_obj})

hold off;


% draw the neurons of each layer in a different color

f=figure;
hold on;
reOrdering = [];

sColors = 'kbyrmg'; %6 colors used
for z= 1:6 
   MP=[];
    ind= find (layerNB==z &MPIndicesTwo'~=0); %find neurons in specific layer (of given types too)
    if (~isempty (ind))
    MP = getMorphIndices(ind, neuron, neuronName);
    maxHA =maxHeightAxon(MP);
    maxHD =maxHeightDendrite(MP);
    
    t(z)= plot (maxHA, maxHD, [sColors( z ) 'x']);
    
    xlabel('Axon Height')
    ylabel('Dendrite Height')
    title ('Correlation per layer')
    
     reOrdering= [reOrdering ind'];
    plotIndex(z)= length(ind); 
    
     else
     
     reOrdering= [reOrdering ind'];
     plotIndex(z)= 0;    
    end
end    
 
legend([t(2) t(3) t(4) t(5) t(6)], 'Layer 2', 'Layer 3', 'Layer 4', 'Layer 5', 'Layer 6');
 
%   datacursormode on
     dcm_obj = datacursormode(f);
     set(dcm_obj,'UpdateFcn',{@myupdatefcntwo,MPIndicesTwo, neuronName,dcm_obj,plotIndex,reOrdering,t})  


