function Layer = getLayerDefinition(LayerFile)
% define Layer Boundaries

%fraction = 1325.81/1200.00;
%fraction = 1.5;

% Layer(6).From = 0*fraction;
% Layer(6).To = 180*fraction;
% 
% Layer(5).From = 180*fraction;
% Layer(5).To = 564*fraction;
% 
% Layer(4).From = 564*fraction;
% Layer(4).To = 804*fraction;
% 
% Layer(3).From = 804*fraction;
% Layer(3).To = 984*fraction;
% 
% Layer(2).From = 984*fraction;
% Layer(2).To = 1104*fraction;
% 
% Layer(1).From = 1104*fraction;
% Layer(1).To = 1200*fraction;

% 
% 
% Layer(6).From = 0;
% Layer(6).To = 180;
% 
% Layer(5).From = 180;
% Layer(5).To = 564;
% 
% Layer(4).From = 564;
% Layer(4).To = 804;
% 
% Layer(3).From = 804;
% Layer(3).To = 984;
% 
% Layer(2).From = 984;
% Layer(2).To = 1104;
% 
% Layer(1).From = 1104;
% Layer(1).To = 1200;
 
 
layerThicknesses = load(LayerFile);
 
Layer(6).From = 0;
Layer(6).To = layerThicknesses(6)+Layer(6).From;

Layer(5).From = Layer(6).To;
Layer(5).To = Layer(5).From+ layerThicknesses(5);


Layer(4).From = Layer(5).To;
Layer(4).To = Layer(4).From+ layerThicknesses(4);


Layer(3).From = Layer(4).To;
Layer(3).To = Layer(3).From+ layerThicknesses(3);


Layer(2).From = Layer(3).To;
Layer(2).To = Layer(2).From+ layerThicknesses(2);

Layer(1).From = Layer(2).To;
Layer(1).To = Layer(1).From+ layerThicknesses(1);


% 
% Layer(6).From = 0;
% Layer(6).To = 445.3752;
% 
% Layer(5).From = 445.3752;
% Layer(5).To = 814.7848;
% 
% Layer(4).From = 814.7848;
% Layer(4).To = 1005.0736;
% 
% Layer(3).From = 1005.376;
% Layer(3).To = 1217.752;
% 
% Layer(2).From = 1217.752;
% Layer(2).To = 1385.6512;
% 
% Layer(1).From = 1385.6512;
% Layer(1).To = 1520;


%Layer(1).To = Layer(1).To + 20;


% 
% 
% Layer(6).From = 0;
% Layer(6).To = 565;
% 
% Layer(5).From = 565;
% Layer(5).To = 1095;
% 
% Layer(4).From = 1095;
% Layer(4).To = 1247;
% 
% Layer(3).From = 1247;
% Layer(3).To = 1522;
% 
% Layer(2).From = 1522;
% Layer(2).To = 1704;
% 
% Layer(1).From = 1704;
% Layer(1).To = 1827;